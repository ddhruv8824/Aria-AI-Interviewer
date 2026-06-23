"use client";

import { useEffect, useState } from "react";
import type { PracticeSession } from "@/lib/types";
import { getApiUrl } from "@/lib/api";

const STORAGE_KEY = "auralis_practice_session";

export function loadPracticeSessionFromUrl(): PracticeSession | null {
  if (typeof window === "undefined") return null;

  const params = new URLSearchParams(window.location.search);
  const email = params.get("email")?.trim() ?? "";
  const companyId = params.get("company")?.trim() ?? "";

  if (email && companyId) {
    const session: PracticeSession = {
      email,
      companyId,
      companyName: companyId,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    return session;
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as PracticeSession;
  } catch {
    /* ignore */
  }
  return null;
}

export function usePracticeSession() {
  const [session, setSession] = useState<PracticeSession | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const loaded = loadPracticeSessionFromUrl();
    if (!loaded) {
      setSession(null);
      setReady(true);
      return;
    }

    fetch(getApiUrl(`/api/v1/platform/companies`))
      .then((r) => r.json())
      .then((companies: Array<{ id: string; name: string }>) => {
        const match = companies.find((c) => c.id === loaded.companyId);
        const next = { ...loaded, companyName: match?.name ?? loaded.companyId };
        setSession(next);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      })
      .catch(() => setSession(loaded))
      .finally(() => setReady(true));
  }, []);

  return { session, ready };
}
