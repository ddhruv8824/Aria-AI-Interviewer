export type Screen = "setup" | "interview" | "coding" | "evaluating" | "results";

export interface PracticeSession {
  email: string;
  companyId: string;
  companyName: string;
}

export type StatusColor = "" | "green" | "blue" | "yellow" | "red";

export interface TranscriptEntry {
  id: string;
  role: "user" | "gemini";
  text: string;
  time: string;
  isStreaming?: boolean;
}

export interface DimensionScore {
  name: string;
  score: number;
  rationale: string;
}

export interface ScorecardReport {
  overall_score?: number;
  hire_recommendation?: string;
  overall_verdict?: string;
  dimensions?: DimensionScore[];
  strengths?: string[];
  improvements?: string[];
}

export interface CodingRoundMessage {
  type: "coding_round";
  problem_id: string;
  time_limit_sec: number;
}

export type WsClientMessage =
  | {
      type: "start";
      resume_context: string;
      job_description_context?: string;
      candidate_name?: string;
      candidate_email?: string;
      company_id?: string;
    }
  | { type: "begin_coding" }
  | {
      type: "coding_submit";
      problem_id: string;
      problem_title: string;
      source_code: string;
      language: string;
      passed_count: number;
      total_count: number;
      all_passed: boolean;
      time_taken_sec: number;
      timed_out: boolean;
    }
  | { type: "audio"; data: string }
  | { type: "stop"; skip_coding?: boolean };

export type WsServerMessage =
  | { type: "connected" }
  | { type: "session_started" }
  | { type: "your_turn" }
  | CodingRoundMessage
  | { type: "audio"; data: string }
  | { type: "transcript_gemini"; text: string; final?: boolean }
  | { type: "transcript_user"; text: string; final?: boolean }
  | { type: "turn_complete" }
  | { type: "interrupted" }
  | { type: "evaluating"; message?: string }
  | { type: "scorecard"; report: ScorecardReport }
  | { type: "error"; message?: string }
  | { type: "session_ended" };
