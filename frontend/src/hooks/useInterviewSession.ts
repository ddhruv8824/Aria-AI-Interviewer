"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { uploadResume, uploadJobDescription, getWsUrl } from "@/lib/api";
import { getCodingProblem, CODING_ROUND_TIME_SEC } from "@/lib/codingProblems";
import type { Problem } from "@/components/CodingQuestion";
import type { RunResponse } from "@/components/CodingQuestion";
import { AudioCapture, AudioPlayer, base64ToBuffer, bufferToBase64 } from "@/lib/audio";
import { INTERVIEWER_NAME } from "@/lib/constants";
import { mergeTranscriptText } from "@/lib/transcript";
import type {
  ScorecardReport,
  Screen,
  StatusColor,
  TranscriptEntry,
  WsClientMessage,
  WsServerMessage,
} from "@/lib/types";

function formatTime(date = new Date()): string {
  return date.toLocaleTimeString("en", { hour12: false });
}

function isPlaceholderText(text: string): boolean {
  const t = text.trim();
  return !t || t === "[inaudible]" || /^\[Audio #\d+\]$/.test(t);
}

export function useInterviewSession(practice: { email: string; companyId: string; companyName: string } | null) {
  const [screen, setScreen] = useState<Screen>("setup");
  const [resumeContext, setResumeContext] = useState("");
  const [resumeStatus, setResumeStatus] = useState({ text: "No resume selected.", kind: "" as "" | "ok" | "err" });
  const [jdStatus, setJdStatus] = useState({ text: "No job description selected.", kind: "" as "" | "ok" | "err" });
  const [statusText, setStatusText] = useState("Connecting…");
  const [statusColor, setStatusColor] = useState<StatusColor>("yellow");
  const [timer, setTimer] = useState("00:00");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [scorecard, setScorecard] = useState<ScorecardReport | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [isSubmittingCoding, setIsSubmittingCoding] = useState(false);
  const [codingProblem, setCodingProblem] = useState<Problem | null>(null);
  const [codingTimeLimitSec, setCodingTimeLimitSec] = useState(CODING_ROUND_TIME_SEC);
  const [codingStartedAt, setCodingStartedAt] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const canSendAudioRef = useRef(false);
  const acceptPlaybackRef = useRef(true);
  const resumeContextRef = useRef("");
  const jobDescriptionContextRef = useRef("");
  const candidateNameRef = useRef("");
  const candidateEmailRef = useRef("");
  const companyIdRef = useRef("");
  const timerIdRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const captureRef = useRef(new AudioCapture());
  const playerRef = useRef(new AudioPlayer());
  const streamingIdRef = useRef<{ gemini: string | null; user: string | null }>({
    gemini: null,
    user: null,
  });

  const setStatus = useCallback((text: string, color: StatusColor = "") => {
    setStatusText(text);
    setStatusColor(color);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerIdRef.current) clearInterval(timerIdRef.current);
    timerIdRef.current = null;
  }, []);

  const startTimer = useCallback(() => {
    const t0 = Date.now();
    stopTimer();
    timerIdRef.current = setInterval(() => {
      const sec = Math.floor((Date.now() - t0) / 1000);
      const mm = String(Math.floor(sec / 60)).padStart(2, "0");
      const ss = String(sec % 60).padStart(2, "0");
      setTimer(`${mm}:${ss}`);
    }, 1000);
  }, [stopTimer]);

  const stopPlayback = useCallback(() => {
    acceptPlaybackRef.current = false;
    playerRef.current.mute();
  }, []);

  const finalizeStreaming = useCallback((roles?: Array<"user" | "gemini">) => {
    const targets = roles ?? (["user", "gemini"] as const);
    const ids = targets
      .map((role) => streamingIdRef.current[role])
      .filter((id): id is string => Boolean(id));

    for (const role of targets) {
      streamingIdRef.current[role] = null;
    }

    if (ids.length === 0) return;

    setTranscript((prev) =>
      prev.map((entry) =>
        ids.includes(entry.id) ? { ...entry, isStreaming: false } : entry,
      ),
    );
  }, []);

  const setTranscriptFinal = useCallback((role: "user" | "gemini", text: string) => {
    const trimmed = text.trim();
    if (isPlaceholderText(trimmed)) return;

    const streamId = streamingIdRef.current[role];
    streamingIdRef.current[role] = null;

    if (streamId) {
      setTranscript((prev) =>
        prev.map((entry) =>
          entry.id === streamId
            ? { ...entry, text: trimmed, isStreaming: false }
            : entry,
        ),
      );
      return;
    }

    const id = `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setTranscript((prev) => [...prev, { id, role, text: trimmed, time: formatTime(), isStreaming: false }]);
  }, []);

  const appendTranscriptChunk = useCallback((role: "user" | "gemini", chunk: string) => {
    const text = chunk.trim();
    if (isPlaceholderText(text)) return;

    let streamId = streamingIdRef.current[role];

    if (!streamId) {
      streamId = `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      streamingIdRef.current[role] = streamId;
      setTranscript((prev) => [
        ...prev,
        { id: streamId!, role, text, time: formatTime(), isStreaming: true },
      ]);
      return;
    }

    setTranscript((prev) =>
      prev.map((entry) =>
        entry.id === streamId
          ? {
              ...entry,
              text: mergeTranscriptText(entry.text, text),
              isStreaming: true,
            }
          : entry,
      ),
    );
  }, []);

  const wsSend = useCallback((msg: WsClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const resetToSetup = useCallback(() => {
    canSendAudioRef.current = false;
    acceptPlaybackRef.current = false;
    captureRef.current.stop();
    playerRef.current.mute();
    stopTimer();
    wsRef.current?.close();
    wsRef.current = null;
    streamingIdRef.current = { gemini: null, user: null };
    setIsEnding(false);
    setIsStarting(false);
    setScreen("setup");
  }, [stopTimer]);

  const handleMessage = useCallback(
    (msg: WsServerMessage) => {
      switch (msg.type) {
        case "connected":
          wsSend({
            type: "start",
            resume_context: resumeContextRef.current,
            job_description_context: jobDescriptionContextRef.current,
            candidate_name: candidateNameRef.current,
            candidate_email: candidateEmailRef.current,
            company_id: companyIdRef.current,
          });
          break;
        case "session_started":
          acceptPlaybackRef.current = true;
          canSendAudioRef.current = false;
          setScreen("interview");
          setStatus(`${INTERVIEWER_NAME} is speaking…`, "blue");
          startTimer();
          break;
        case "your_turn":
          canSendAudioRef.current = true;
          setStatus("Listening…", "green");
          break;
        case "audio":
          if (!acceptPlaybackRef.current) return;
          playerRef.current.play(base64ToBuffer(msg.data));
          setStatus("Speaking…", "blue");
          break;
        case "transcript_gemini":
          if (msg.final) {
            setTranscriptFinal("gemini", msg.text);
          } else {
            appendTranscriptChunk("gemini", msg.text);
          }
          break;
        case "transcript_user":
          if (!canSendAudioRef.current && !msg.final) break;
          if (msg.final) {
            setTranscriptFinal("user", msg.text);
          } else {
            appendTranscriptChunk("user", msg.text);
          }
          break;
        case "turn_complete":
          finalizeStreaming();
          if (canSendAudioRef.current) {
            setStatus("Listening…", "green");
          }
          break;
        case "interrupted":
          playerRef.current.stop();
          finalizeStreaming(["gemini"]);
          if (canSendAudioRef.current) {
            setStatus("Listening…", "green");
          } else {
            setStatus(`${INTERVIEWER_NAME} is speaking…`, "blue");
          }
          break;
        case "coding_round":
          stopPlayback();
          captureRef.current.stop();
          canSendAudioRef.current = false;
          finalizeStreaming();
          stopTimer();
          setCodingProblem(getCodingProblem(msg.problem_id));
          setCodingTimeLimitSec(msg.time_limit_sec);
          setCodingStartedAt(Date.now());
          setScreen("coding");
          break;
        case "evaluating":
          stopPlayback();
          captureRef.current.stop();
          canSendAudioRef.current = false;
          finalizeStreaming();
          setScreen("evaluating");
          stopTimer();
          break;
        case "scorecard":
          stopPlayback();
          setScorecard(msg.report);
          setScreen("results");
          break;
        case "error":
          stopPlayback();
          setStatus(msg.message || "Error", "red");
          alert(msg.message || "Session error");
          resetToSetup();
          break;
        case "session_ended":
          stopPlayback();
          captureRef.current.stop();
          canSendAudioRef.current = false;
          break;
      }
    },
    [
      appendTranscriptChunk,
      finalizeStreaming,
      resetToSetup,
      setStatus,
      setTranscriptFinal,
      startTimer,
      stopPlayback,
      stopTimer,
      wsSend,
    ],
  );

  const connectSocket = useCallback((): Promise<void> => {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(getWsUrl());
      wsRef.current = ws;

      ws.onopen = () => resolve();
      ws.onerror = () => reject(new Error("WebSocket connection failed"));
      ws.onmessage = (ev) => {
        try {
          handleMessage(JSON.parse(ev.data) as WsServerMessage);
        } catch {
          /* ignore malformed */
        }
      };
      ws.onclose = () => {
        canSendAudioRef.current = false;
        acceptPlaybackRef.current = false;
        captureRef.current.stop();
        playerRef.current.mute();
      };
    });
  }, [handleMessage]);

  const handleResumeUpload = useCallback(async (file: File) => {
    setResumeStatus({ text: `Parsing ${file.name}…`, kind: "" });
    try {
      const data = await uploadResume(file);
      resumeContextRef.current = data.context_block;
      candidateNameRef.current = data.candidate_name?.trim() ?? "";
      setResumeContext(data.context_block);
      setResumeStatus({ text: `Loaded: ${file.name} (${data.skill_count} skills)`, kind: "ok" });
    } catch (err) {
      resumeContextRef.current = "";
      if (!candidateNameRef.current) {
        candidateNameRef.current = "";
      }
      setResumeContext("");
      setResumeStatus({
        text: `Failed: ${err instanceof Error ? err.message : "Unknown error"}`,
        kind: "err",
      });
    }
  }, []);

  const handleJobDescriptionUpload = useCallback(async (file: File) => {
    setJdStatus({ text: `Parsing ${file.name}…`, kind: "" });
    try {
      const data = await uploadJobDescription(file);
      jobDescriptionContextRef.current = data.context_block;
      setJdStatus({
        text: `Loaded: ${file.name} (${data.char_count.toLocaleString()} chars)`,
        kind: "ok",
      });
    } catch (err) {
      jobDescriptionContextRef.current = "";
      setJdStatus({
        text: `Failed: ${err instanceof Error ? err.message : "Unknown error"}`,
        kind: "err",
      });
    }
  }, []);

  const startInterview = useCallback(async () => {
    setIsStarting(true);
    canSendAudioRef.current = false;
    acceptPlaybackRef.current = true;
    playerRef.current.reset();
    playerRef.current.prime();
    setStatus("Connecting…", "yellow");
    setScreen("interview");
    setTranscript([]);
    streamingIdRef.current = { gemini: null, user: null };

    try {
      await captureRef.current.start((buffer) => {
        if (!canSendAudioRef.current || wsRef.current?.readyState !== WebSocket.OPEN) return;
        wsSend({ type: "audio", data: bufferToBase64(buffer) });
      });
      await connectSocket();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start";
      alert(message.includes("Permission") ? "Microphone blocked. Allow mic access in browser settings." : message);
      resetToSetup();
    } finally {
      setIsStarting(false);
    }
  }, [connectSocket, resetToSetup, setStatus, wsSend]);

  const beginCodingRound = useCallback(() => {
    if (isEnding) return;
    canSendAudioRef.current = false;
    stopPlayback();
    captureRef.current.stop();
    finalizeStreaming();
    setIsEnding(true);
    setStatus("Starting coding round…", "yellow");
    wsSend({ type: "begin_coding" });
  }, [finalizeStreaming, isEnding, setStatus, stopPlayback, wsSend]);

  const skipToEvaluation = useCallback(() => {
    if (isEnding) return;
    canSendAudioRef.current = false;
    stopPlayback();
    captureRef.current.stop();
    finalizeStreaming();
    stopTimer();
    setIsEnding(true);
    setStatus("Finishing…", "yellow");
    wsSend({ type: "stop", skip_coding: true });
  }, [finalizeStreaming, isEnding, setStatus, stopPlayback, stopTimer, wsSend]);

  const submitCodingRound = useCallback(
    async (payload: {
      source_code: string;
      language: string;
      result: RunResponse | null;
      time_taken_sec: number;
      timed_out: boolean;
    }) => {
      if (isSubmittingCoding || !codingProblem) return;
      setIsSubmittingCoding(true);
      setScreen("evaluating");
      wsSend({
        type: "coding_submit",
        problem_id: codingProblem.id ?? "unknown",
        problem_title: codingProblem.title,
        source_code: payload.source_code,
        language: payload.language,
        passed_count: payload.result?.passed_count ?? 0,
        total_count: payload.result?.total_count ?? codingProblem.testCases.length,
        all_passed: payload.result?.all_passed ?? false,
        time_taken_sec: payload.time_taken_sec,
        timed_out: payload.timed_out,
      });
    },
    [codingProblem, isSubmittingCoding, wsSend],
  );

  const endInterview = useCallback(() => {
    beginCodingRound();
  }, [beginCodingRound]);

  const restart = useCallback(() => {
    window.location.reload();
  }, []);

  useEffect(() => {
    if (practice) {
      candidateEmailRef.current = practice.email;
      companyIdRef.current = practice.companyId;
    }
  }, [practice]);

  useEffect(() => {
    return () => {
      captureRef.current.stop();
      playerRef.current.mute();
      wsRef.current?.close();
    };
  }, [stopTimer]);

  return {
    screen,
    resumeStatus,
    jdStatus,
    statusText,
    statusColor,
    timer,
    transcript,
    scorecard,
    isStarting,
    isEnding,
    isSubmittingCoding,
    codingProblem,
    codingTimeLimitSec,
    codingStartedAt,
    handleResumeUpload,
    handleJobDescriptionUpload,
    startInterview,
    beginCodingRound,
    skipToEvaluation,
    submitCodingRound,
    endInterview,
    restart,
    practice,
  };
}
