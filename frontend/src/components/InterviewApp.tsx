"use client";

import { CodingRoundScreen } from "@/components/CodingRoundScreen";
import { EvaluatingScreen } from "@/components/EvaluatingScreen";
import { CodeEditorPreview } from "@/components/CodeEditorPreview";
import { Header } from "@/components/Header";
import { InterviewScreen } from "@/components/InterviewScreen";
import { PracticeGateScreen } from "@/components/PracticeGateScreen";
import { ResultsScreen } from "@/components/ResultsScreen";
import { SetupScreen } from "@/components/SetupScreen";
import { useInterviewSession } from "@/hooks/useInterviewSession";
import { usePracticeSession } from "@/hooks/usePracticeSession";

export function InterviewApp() {
  const { session: practice, ready } = usePracticeSession();
  const interview = useInterviewSession(practice);

  return (
    <main className="flex min-h-screen flex-col overflow-x-hidden text-base">
      <Header practice={practice} />
      <div className="flex-grow pb-16 pt-[120px]">
        <div className="mx-auto max-w-[1280px] space-y-10 px-8">
          {!ready && (
            <div className="rounded-3xl border border-auralis bg-card-auralis p-10 text-center text-secondary-auralis">
              Loading your practice session…
            </div>
          )}
          {ready && !practice && <PracticeGateScreen />}
          {ready && practice && interview.screen === "setup" && (
            <>
              <SetupScreen
                practice={practice}
                resumeStatus={interview.resumeStatus}
                jdStatus={interview.jdStatus}
                isStarting={interview.isStarting}
                onResumeSelect={interview.handleResumeUpload}
                onJobDescriptionSelect={interview.handleJobDescriptionUpload}
                onStart={interview.startInterview}
              />
              <CodeEditorPreview />
            </>
          )}
          {ready && practice && interview.screen === "interview" && (
            <InterviewScreen
              statusText={interview.statusText}
              statusColor={interview.statusColor}
              timer={interview.timer}
              transcript={interview.transcript}
              isEnding={interview.isEnding}
              onStartCoding={interview.beginCodingRound}
              onSkipCoding={interview.skipToEvaluation}
            />
          )}
          {ready &&
            practice &&
            interview.screen === "coding" &&
            interview.codingProblem &&
            interview.codingStartedAt > 0 && (
              <CodingRoundScreen
                problem={interview.codingProblem}
                timeLimitSec={interview.codingTimeLimitSec}
                startedAt={interview.codingStartedAt}
                isSubmitting={interview.isSubmittingCoding}
                onSubmit={interview.submitCodingRound}
              />
            )}
          {ready && practice && interview.screen === "evaluating" && <EvaluatingScreen />}
          {ready && practice && interview.screen === "results" && (
            <ResultsScreen report={interview.scorecard} onRestart={interview.restart} />
          )}
        </div>
      </div>
    </main>
  );
}
