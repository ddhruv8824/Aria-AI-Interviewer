const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export function getHomeUrl(): string {
  return process.env.NEXT_PUBLIC_HOME_URL ?? "http://127.0.0.1:4000";
}

export function getApiUrl(path: string): string {
  return `${API_URL.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
}

export function getWsUrl(): string {
  return process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8000/ws/session";
}

export function getCodeRunUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  return `${base.replace(/\/$/, "")}/api/v1/code`;
}

export interface ResumeContextResponse {
  context_block: string;
  candidate_name?: string | null;
  skill_count: number;
}

export interface JobDescriptionContextResponse {
  context_block: string;
  char_count: number;
}

export async function uploadResume(file: File): Promise<ResumeContextResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(getApiUrl("/api/v1/resume/context"), {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    throw new Error(`Server returned ${res.status}`);
  }

  return res.json();
}

export async function uploadJobDescription(file: File): Promise<JobDescriptionContextResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(getApiUrl("/api/v1/job-description/context"), {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    throw new Error(`Server returned ${res.status}`);
  }

  return res.json();
}
