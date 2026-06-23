"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import type { Company } from "@/lib/api";

interface EmailModalProps {
  company: Company | null;
  open: boolean;
  onClose: () => void;
  onSubmit: (email: string) => Promise<void>;
}

export function EmailModal({ company, open, onClose, onSubmit }: EmailModalProps) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setEmail("");
      setError("");
      setLoading(false);
    }
  }, [open, company?.id]);

  if (!open || !company) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await onSubmit(email.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-3xl border border-auralis bg-card-auralis p-8 shadow-xl">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-secondary-auralis">
              Start practising
            </p>
            <h3 className="mt-1 text-2xl font-semibold tracking-tight text-primary">
              {company.name} interview
            </h3>
            <p className="mt-2 text-sm text-secondary-auralis">
              Enter your email to continue to the voice + coding practice app.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-auralis p-2 text-primary hover:bg-surface-variant"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@email.com"
            className="w-full rounded-2xl border border-auralis bg-panel-auralis px-4 py-3 text-sm text-primary outline-none focus:border-outline"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-full bg-primary px-6 py-3 text-sm font-medium text-on-primary transition-all hover:bg-black/80 disabled:opacity-60"
          >
            {loading ? "Starting…" : "Continue to interview app →"}
          </button>
        </form>
      </div>
    </div>
  );
}
