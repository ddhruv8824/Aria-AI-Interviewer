'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Mic,
  Code2,
  Building2,
  MessageSquarePlus,
  BookOpen,
  ArrowRight,
  Sparkles,
  Terminal,
  CheckCircle2,
} from 'lucide-react';
import { motion } from 'motion/react';
import { EmailModal } from '@/components/EmailModal';
import {
  fetchBlogs,
  fetchCompanies,
  fetchQuestions,
  interviewAppUrl,
  registerPractice,
  submitBlog,
  submitQuestion,
  type BlogPost,
  type CommunityQuestion,
  type Company,
} from '@/lib/api';

export default function AuralisHomePage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [questions, setQuestions] = useState<CommunityQuestion[]>([]);
  const [blogs, setBlogs] = useState<BlogPost[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [filterCompany, setFilterCompany] = useState<string>('all');

  const [qCompany, setQCompany] = useState('amazon');
  const [qText, setQText] = useState('');
  const [qCategory, setQCategory] = useState('behavioral');
  const [qStatus, setQStatus] = useState('');

  const [bCompany, setBCompany] = useState('google');
  const [bTitle, setBTitle] = useState('');
  const [bBody, setBBody] = useState('');
  const [bStatus, setBStatus] = useState('');

  useEffect(() => {
    fetchCompanies().then(setCompanies).catch(console.error);
    fetchQuestions().then(setQuestions).catch(console.error);
    fetchBlogs().then(setBlogs).catch(console.error);
  }, []);

  const openPractice = useCallback((company: Company) => {
    setSelectedCompany(company);
    setModalOpen(true);
  }, []);

  const handleRegister = useCallback(
    async (email: string) => {
      if (!selectedCompany) return;
      await registerPractice(email, selectedCompany.id);
      window.location.href = interviewAppUrl(email, selectedCompany.id);
    },
    [selectedCompany],
  );

  const filteredQuestions =
    filterCompany === 'all' ? questions : questions.filter((q) => q.company_id === filterCompany);

  const filteredBlogs =
    filterCompany === 'all' ? blogs : blogs.filter((b) => b.company_id === filterCompany);

  return (
    <main className="min-h-screen flex flex-col overflow-x-hidden text-base">
      <nav className="fixed top-0 z-50 w-full border-b border-zinc-200/60 bg-[#F7F7F5]/80 backdrop-blur-md">
        <div className="mx-auto flex h-[72px] max-w-[1280px] items-center justify-between px-8">
          <a href="#" className="text-[20px] font-bold tracking-tighter text-zinc-900">
            Auralis
          </a>
          <div className="hidden items-center gap-6 md:flex">
            {[
              ['#practice', 'Practice'],
              ['#companies', 'Companies'],
              ['#editor', 'Code editor'],
              ['#community', 'Community'],
              ['#blogs', 'Experiences'],
            ].map(([href, label]) => (
              <a
                key={href}
                href={href}
                className="text-sm font-medium tracking-tight text-zinc-500 transition-colors hover:text-zinc-900"
              >
                {label}
              </a>
            ))}
          </div>
        </div>
      </nav>

      <div className="flex-grow pt-[120px] pb-16">
        {/* Hero */}
        <section id="practice" className="mx-auto mb-[100px] max-w-[1280px] px-8">
          <div className="grid grid-cols-1 items-start gap-10 lg:grid-cols-12">
            <div className="lg:col-span-7">
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="inline-flex rounded-full bg-surface-variant px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-primary"
              >
                AI mock interviews
              </motion.span>
              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 text-5xl font-semibold tracking-tighter text-primary md:text-[72px] md:leading-[1.05]"
              >
                Practise interviews that feel real
              </motion.h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-secondary-auralis">
                Voice interviews with Aria, timed LeetCode-style coding rounds, and company-specific
                question banks — built from real candidate experiences.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <a
                  href="#companies"
                  className="inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-medium text-on-primary transition-all hover:bg-black/80"
                >
                  Start practising <ArrowRight className="h-4 w-4" />
                </a>
              </div>
            </div>
            <div className="lg:col-span-5">
              <div className="rounded-3xl border border-auralis bg-panel-auralis p-6">
                <div className="mb-4 flex items-center gap-2 text-sm font-medium text-primary">
                  <Sparkles className="h-4 w-4" /> What you get
                </div>
                {[
                  'Voice mock interview with Indian English AI interviewer',
                  'Resume + job description aware questions',
                  '20-minute coding round (Python / JavaScript)',
                  'Company-specific community question packs',
                ].map((item) => (
                  <div key={item} className="mb-3 flex gap-3 text-sm text-secondary-auralis">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Companies */}
        <section id="companies" className="mx-auto mb-[100px] max-w-[1280px] px-8">
          <SectionHeader
            eyebrow="Company tracks"
            title="Practise for top companies"
            body="Pick a company to load interview style, community questions, and experience blogs into your AI session."
          />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {companies.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => openPractice(c)}
                className="group rounded-2xl border border-auralis bg-card-auralis p-6 text-left transition-all hover:border-outline hover:shadow-sm"
              >
                <div
                  className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl text-lg font-bold text-white"
                  style={{ backgroundColor: c.color }}
                >
                  {c.name.charAt(0)}
                </div>
                <h3 className="text-xl font-semibold tracking-tight text-primary">{c.name}</h3>
                <p className="mt-2 text-sm text-secondary-auralis">{c.tagline}</p>
                <p className="mt-4 text-xs font-semibold uppercase tracking-widest text-secondary-auralis group-hover:text-primary">
                  Start practising →
                </p>
              </button>
            ))}
          </div>
        </section>

        {/* Code editor showcase */}
        <section id="editor" className="mx-auto mb-[100px] max-w-[1280px] px-8">
          <SectionHeader
            eyebrow="Coding round"
            title="LeetCode-style editor built in"
            body="After the verbal round, solve timed challenges with run tests and submit — just like a real onsite."
          />
          <div className="overflow-hidden rounded-3xl border border-auralis bg-panel-auralis">
            <div className="grid lg:grid-cols-2">
              <div className="border-b border-auralis p-8 lg:border-b-0 lg:border-r">
                <div className="mb-6 flex items-center gap-2 text-primary">
                  <Terminal className="h-5 w-5" />
                  <span className="font-semibold">Classify a Number · Easy</span>
                </div>
                <pre className="overflow-x-auto rounded-2xl border border-auralis bg-[#fafafa] p-4 text-sm leading-relaxed text-primary">
{`n = int(input())
if n > 0:
    print("Positive")
elif n < 0:
    print("Negative")
else:
    print("Zero")`}
                </pre>
                <p className="mt-4 text-sm text-secondary-auralis">
                  Python & JavaScript · local test runner · 20 min timer
                </p>
              </div>
              <div className="flex flex-col justify-center gap-6 p-8">
                <div className="flex items-center gap-4 rounded-2xl border border-auralis bg-surface p-5">
                  <Mic className="h-8 w-8 text-primary" strokeWidth={1.5} />
                  <div>
                    <div className="font-medium text-primary">1. Voice with Aria</div>
                    <div className="text-sm text-secondary-auralis">Behavioral + technical Q&A</div>
                  </div>
                </div>
                <div className="flex items-center gap-4 rounded-2xl border border-auralis bg-surface p-5">
                  <Code2 className="h-8 w-8 text-primary" strokeWidth={1.5} />
                  <div>
                    <div className="font-medium text-primary">2. Timed coding round</div>
                    <div className="text-sm text-secondary-auralis">Run tests → submit answer</div>
                  </div>
                </div>
                <div className="flex items-center gap-4 rounded-2xl border border-auralis bg-surface p-5">
                  <Building2 className="h-8 w-8 text-primary" strokeWidth={1.5} />
                  <div>
                    <div className="font-medium text-primary">3. Company-aware AI</div>
                    <div className="text-sm text-secondary-auralis">Uses community question data</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Community questions */}
        <section id="community" className="mx-auto mb-[100px] max-w-[1280px] px-8">
          <SectionHeader
            eyebrow="Community"
            title="Anonymous company questions"
            body="Interviewed or work at these companies? Share questions anonymously to help others prepare."
          />
          <div className="mb-8 grid gap-8 lg:grid-cols-2">
            <form
              className="rounded-2xl border border-auralis bg-card-auralis p-6"
              onSubmit={async (e) => {
                e.preventDefault();
                setQStatus('');
                try {
                  await submitQuestion(qCompany, qText, qCategory);
                  setQText('');
                  setQStatus('Thanks — question added!');
                  setQuestions(await fetchQuestions());
                } catch {
                  setQStatus('Failed to submit.');
                }
              }}
            >
              <div className="mb-4 flex items-center gap-2 text-primary">
                <MessageSquarePlus className="h-5 w-5" />
                <span className="font-semibold">Submit a question</span>
              </div>
              <select
                value={qCompany}
                onChange={(e) => setQCompany(e.target.value)}
                className="mb-3 w-full rounded-xl border border-auralis bg-panel-auralis px-3 py-2 text-sm"
              >
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <select
                value={qCategory}
                onChange={(e) => setQCategory(e.target.value)}
                className="mb-3 w-full rounded-xl border border-auralis bg-panel-auralis px-3 py-2 text-sm"
              >
                <option value="behavioral">Behavioral</option>
                <option value="technical">Technical</option>
                <option value="coding">Coding</option>
                <option value="system_design">System design</option>
                <option value="culture">Culture</option>
              </select>
              <textarea
                required
                value={qText}
                onChange={(e) => setQText(e.target.value)}
                placeholder="What were you asked?"
                rows={4}
                className="mb-3 w-full rounded-xl border border-auralis bg-panel-auralis px-3 py-2 text-sm"
              />
              <button type="submit" className="rounded-full bg-primary px-5 py-2 text-sm font-medium text-on-primary">
                Submit anonymously
              </button>
              {qStatus && <p className="mt-2 text-sm text-emerald-700">{qStatus}</p>}
            </form>

            <div>
              <select
                value={filterCompany}
                onChange={(e) => setFilterCompany(e.target.value)}
                className="mb-4 rounded-full border border-auralis bg-surface px-4 py-2 text-sm"
              >
                <option value="all">All companies</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <div className="max-h-[420px] space-y-3 overflow-y-auto no-scrollbar">
                {filteredQuestions.map((q) => (
                  <div key={q.id} className="rounded-xl border border-auralis bg-panel-auralis p-4">
                    <div className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-secondary-auralis">
                      {companies.find((c) => c.id === q.company_id)?.name ?? q.company_id} · {q.category}
                    </div>
                    <p className="text-sm text-primary">{q.question}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Blogs */}
        <section id="blogs" className="mx-auto max-w-[1280px] px-8">
          <SectionHeader
            eyebrow="Reader"
            title="Interview experiences"
            body="Read and share what the loop was really like — feeds our AI with authentic company context."
          />
          <div className="mb-8 grid gap-8 lg:grid-cols-2">
            <form
              className="rounded-2xl border border-auralis bg-card-auralis p-6"
              onSubmit={async (e) => {
                e.preventDefault();
                setBStatus('');
                try {
                  await submitBlog(bCompany, bTitle, bBody, 'Anonymous');
                  setBTitle('');
                  setBBody('');
                  setBStatus('Experience published!');
                  setBlogs(await fetchBlogs());
                } catch {
                  setBStatus('Failed to publish.');
                }
              }}
            >
              <div className="mb-4 flex items-center gap-2 text-primary">
                <BookOpen className="h-5 w-5" />
                <span className="font-semibold">Share your experience</span>
              </div>
              <select
                value={bCompany}
                onChange={(e) => setBCompany(e.target.value)}
                className="mb-3 w-full rounded-xl border border-auralis bg-panel-auralis px-3 py-2 text-sm"
              >
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <input
                required
                value={bTitle}
                onChange={(e) => setBTitle(e.target.value)}
                placeholder="Title e.g. L4 loop recap"
                className="mb-3 w-full rounded-xl border border-auralis bg-panel-auralis px-3 py-2 text-sm"
              />
              <textarea
                required
                value={bBody}
                onChange={(e) => setBBody(e.target.value)}
                placeholder="What happened in your interview?"
                rows={5}
                className="mb-3 w-full rounded-xl border border-auralis bg-panel-auralis px-3 py-2 text-sm"
              />
              <button type="submit" className="rounded-full bg-primary px-5 py-2 text-sm font-medium text-on-primary">
                Publish anonymously
              </button>
              {bStatus && <p className="mt-2 text-sm text-emerald-700">{bStatus}</p>}
            </form>

            <div className="space-y-4">
              {filteredBlogs.map((b) => (
                <article key={b.id} className="rounded-2xl border border-auralis bg-panel-auralis p-6">
                  <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-secondary-auralis">
                    {companies.find((c) => c.id === b.company_id)?.name ?? b.company_id} · {b.author_label}
                  </div>
                  <h3 className="text-lg font-semibold text-primary">{b.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-secondary-auralis">{b.excerpt}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
      </div>

      <footer className="border-t border-auralis py-8 text-center text-sm text-secondary-auralis">
        Auralis · Practise interviews · Homepage :4000 · App :3000
      </footer>

      <EmailModal
        company={selectedCompany}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleRegister}
      />
    </main>
  );
}

function SectionHeader({
  eyebrow,
  title,
  body,
}: {
  eyebrow: string;
  title: string;
  body: string;
}) {
  return (
    <div className="mb-10 grid gap-6 lg:grid-cols-12 lg:items-end">
      <div className="lg:col-span-7">
        <span className="rounded-full bg-surface-variant px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-primary">
          {eyebrow}
        </span>
        <h2 className="mt-4 text-4xl font-semibold tracking-tighter text-primary md:text-[48px]">
          {title}
        </h2>
      </div>
      <p className="text-base leading-relaxed text-secondary-auralis lg:col-span-5">{body}</p>
    </div>
  );
}
