import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Terms & Conditions — ProbeIQ',
  description: 'The terms governing the use of the ProbeIQ interview platform.',
}

const sections = [
  {
    title: 'Last updated',
    body: 'These Terms & Conditions were last updated on August 9, 2026.',
  },
  {
    title: '1. Acceptance of terms',
    body: 'By accessing or using ProbeIQ, you agree to be bound by these terms. If you do not agree, do not use the platform.',
  },
  {
    title: '2. Description of service',
    body: 'ProbeIQ conducts multi-turn technical interviews and produces feedback reports based on candidate data you provide. Interview content is generated with the assistance of AI language models, with an offline fallback when no model is available.',
  },
  {
    title: '3. Use of data',
    body: 'You are responsible for ensuring you have the right to process candidate data you load into ProbeIQ, and for complying with applicable data protection laws. ProbeIQ processes data only to provide the interview and feedback service.',
  },
  {
    title: '4. AI-generated content',
    body: 'Questions, responses, and feedback are AI-generated and may contain errors or omissions. Results should be reviewed by a human before any hiring decision is made. ProbeIQ is provided as a decision-support tool, not a sole basis for employment decisions.',
  },
  {
    title: '5. Acceptable use',
    body: 'You agree not to misuse the platform, attempt to disrupt service, probe unauthorized data, or use the tool to discriminate unlawfully against candidates.',
  },
  {
    title: '6. No warranty',
    body: 'ProbeIQ is provided "as is" without warranties of any kind, express or implied. We do not warrant that the service will be uninterrupted, error-free, or that results will be accurate.',
  },
  {
    title: '7. Limitation of liability',
    body: 'To the fullest extent permitted by law, ProbeIQ shall not be liable for any indirect, incidental, or consequential damages arising from use of the platform or reliance on its feedback.',
  },
  {
    title: '8. Contact',
    body: 'Questions about these terms? Contact the account owner who provisioned your ProbeIQ instance.',
  },
]

export default function TermsPage() {
  return (
    <main className="min-h-dvh bg-[#F8FAFC] text-[#0F172A]">
      <header className="sticky top-0 z-20 bg-white/80 backdrop-blur-xl border-b border-[#E4E7EB]">
        <nav className="max-w-3xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#1E3A5F] flex items-center justify-center
              text-white text-sm font-bold shadow-sm">PI</div>
            <span className="font-bold text-lg tracking-tight">ProbeIQ</span>
          </Link>
          <Link href="/" className="text-sm text-slate-500 hover:text-[#2563EB] transition-colors">Back home</Link>
        </nav>
      </header>

      <article className="max-w-3xl mx-auto px-4 sm:px-6 py-14">
        <p className="text-xs font-semibold text-[#2563EB] uppercase tracking-widest">Legal</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight">Terms & Conditions</h1>
        <p className="mt-3 text-slate-600">The terms and conditions governing your use of the ProbeIQ interview platform.</p>

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
          <p className="text-xs text-slate-400">© ProbeIQ · Terms & Conditions</p>
          <div className="flex items-center gap-5 text-xs text-slate-400">
            <Link href="/privacy" className="hover:text-[#2563EB] transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-[#2563EB] transition-colors">Terms</Link>
          </div>
        </div>
      </footer>
    </main>
  )
}