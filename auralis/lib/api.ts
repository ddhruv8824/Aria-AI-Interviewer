const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
export const INTERVIEW_APP_URL =
  process.env.NEXT_PUBLIC_INTERVIEW_APP_URL ?? "http://127.0.0.1:3000";

export function getApiUrl(path: string): string {
  return `${API_URL.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
}

export interface Company {
  id: string;
  name: string;
  tagline: string;
  color: string;
  focus_areas: string[];
}

export interface CommunityQuestion {
  id: string;
  company_id: string;
  category: string;
  question: string;
  source: string;
  created_at: string;
}

export interface BlogPost {
  id: string;
  company_id: string;
  title: string;
  author_label: string;
  excerpt: string;
  body: string;
  created_at: string;
}

export async function fetchCompanies(): Promise<Company[]> {
  const res = await fetch(getApiUrl("/api/v1/platform/companies"));
  if (!res.ok) throw new Error("Failed to load companies");
  return res.json();
}

export async function fetchQuestions(companyId?: string): Promise<CommunityQuestion[]> {
  const q = companyId ? `?company_id=${encodeURIComponent(companyId)}` : "";
  const res = await fetch(getApiUrl(`/api/v1/platform/questions${q}`));
  if (!res.ok) throw new Error("Failed to load questions");
  return res.json();
}

export async function fetchBlogs(companyId?: string): Promise<BlogPost[]> {
  const q = companyId ? `?company_id=${encodeURIComponent(companyId)}` : "";
  const res = await fetch(getApiUrl(`/api/v1/platform/blogs${q}`));
  if (!res.ok) throw new Error("Failed to load blogs");
  return res.json();
}

export async function registerPractice(email: string, companyId: string) {
  const res = await fetch(getApiUrl("/api/v1/platform/register"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, company_id: companyId }),
  });
  if (!res.ok) {
    const data = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(data.detail ?? "Registration failed");
  }
  return res.json();
}

export async function submitQuestion(companyId: string, question: string, category: string) {
  const res = await fetch(getApiUrl("/api/v1/platform/questions"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_id: companyId, question, category }),
  });
  if (!res.ok) throw new Error("Failed to submit question");
  return res.json();
}

export async function submitBlog(
  companyId: string,
  title: string,
  body: string,
  authorLabel: string,
) {
  const res = await fetch(getApiUrl("/api/v1/platform/blogs"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      company_id: companyId,
      title,
      body,
      author_label: authorLabel,
    }),
  });
  if (!res.ok) throw new Error("Failed to submit blog");
  return res.json();
}

export function interviewAppUrl(email: string, companyId: string): string {
  const base = INTERVIEW_APP_URL.replace(/\/$/, "");
  const params = new URLSearchParams({ email, company: companyId });
  return `${base}/?${params.toString()}`;
}
