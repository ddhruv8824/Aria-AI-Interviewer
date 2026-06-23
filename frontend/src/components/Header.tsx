import { getApiUrl, getHomeUrl } from "@/lib/api";
import type { PracticeSession } from "@/lib/types";

interface HeaderProps {
  practice?: PracticeSession | null;
}

export function Header({ practice }: HeaderProps) {
  return (
    <nav className="fixed top-0 z-50 w-full border-b border-zinc-200/60 bg-[#F7F7F5]/80 backdrop-blur-md transition-all">
      <div className="mx-auto flex h-[72px] max-w-[1280px] items-center justify-between px-8">
        <div className="flex items-center gap-12">
          <a href={getHomeUrl()} className="text-[20px] font-bold tracking-tighter text-zinc-900">
            Auralis
          </a>
          <div className="hidden items-center gap-6 md:flex">
            <span className="text-sm font-medium tracking-tight text-zinc-500">
              {practice ? `${practice.companyName} · Voice Interview` : "Voice Interview"}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <a
            className="hidden text-sm font-medium tracking-tight text-zinc-500 transition-colors duration-200 hover:text-zinc-900 sm:inline"
            href={getApiUrl("/docs")}
            target="_blank"
            rel="noreferrer"
          >
            API Docs
          </a>
          <a
            className="hidden text-sm font-medium tracking-tight text-zinc-500 transition-colors duration-200 hover:text-zinc-900 sm:inline"
            href={getApiUrl("/api/v1/health")}
            target="_blank"
            rel="noreferrer"
          >
            Health
          </a>
        </div>
      </div>
    </nav>
  );
}
