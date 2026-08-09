import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Privacy Policy — ProbeIQ',
  description: 'How ProbeIQ collects, uses, and protects candidate interview data.',
}

const sections = [
  {
    title: 'Last updated',
    body: 'This Privacy Policy was last updated on August 9, 2026.',
  },
  {
    title: '1. Information we collect',
    body: 'ProbeIQ processes candidate profile data (name, job role, years of experience, education) and the interview transcripts produced during an interview session. Candidate data is loaded from your own data files (e.g. candidates.json) — it is not collected from public sources.',
  },
  {
    title: '2. How we use information',
    body: 'Interview data is used solely to conduct the interview, adapt questioning to the candidate\'s background, and generate the final feedback report. We do not sell, rent, or trade your data.',
  },
  {
    title: '3. LLM processing',
    body: 'Part of an interview session, interview turns may be sent to a third-party language model provider (e.g. OpenRouter or a local model) to generate the next question or response. When an API key is unavailable, the system falls back to an offline mock interviewer and no data leaves your machine.',
  },
  {
    title: '4. Session storage',
    body: 'Active interview sessions are held in in-memory storage only and are lost when the server restarts. The frontend stores your current session in your browser\'s local storage so the interview page can resume; you can clear it at any time by clearing your browser data.',
  },
  {
    title: '5. Data retention',
    body: 'We do not operate a retention backend. Interview records persist only as long as the server process is running and the browser session remains stored locally.',
  },
  {
    title: '6. How to contact us',
    body: 'If you have questions about this policy or your interview data, contact the account owner who set up your ProbeIQ instance.',
  },
]

export default function PrivacyPage() {
  return (
    <main className="min-h-dvh bg-[#F8FAFC] text-[#0F172A]">
      <header className="sticky top-0 z-20 bg-white/90 backdrop-blur-xl border-b border-[#E4E7EB]">
        <nav className="max-w-3xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#1E3A5F] flex items-center justify-center
              text-white text-sm font-bold shadow-sm">PI</div>
            <span className="font-bold text-lg tracking-tight">ProbeIQ</span>
          </Link>
          <Link href="/" className="text-sm text-slate-500 hover:text-[#2563EB] transition-colors">← Back home</Link>
        </nav>
      </header>

      <article className="max-w-3xl mx-auto px-4 sm:px-6 py-14">
        <p className="text-xs font-semibold text-[#2563EB] uppercase tracking-widest">Legal</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight">Privacy Policy</h1>
        <p className="mt-3 text-slate-600">ProbeIQ is a technical interview tool. This policy explains how it handles the data involved in running an interview.</p>

        <div className="mt-10 flex flex-col gap-6">
          {sections.map(s => (
            <section key={s.title} className="bg-white border border-[#E4E7EB] rounded-2xl p-6">
              <h2 className="font-semibold text-lg">{s.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{s.body}</p>
            </section>
          ))}
        </div>
      </article>

      <footer className="border-t border-[#E4E7EB] bg-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-xs text-slate-400">ProbeIQ · Privacy Policy</p>
          <div className="flex items-center gap-5 text-xs text-slate-400">
            <Link href="/privacy" className="hover:text-[#2563EB] transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-[#2563EB] transition-colors">Terms</Link>
          </div>
        </div>
      </footer>
    </main>
  )
}