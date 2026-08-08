'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import type { Feedback } from '@/lib/types'

function List({ items, bulletColor }: { items: string[]; bulletColor: string }) {
  if (!items?.length) return <p className="text-sm text-slate-400">None noted</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2 text-sm leading-relaxed">
          <span className={`${bulletColor} font-bold shrink-0 mt-0.5`}>•</span>
          <span className="text-[#0F172A]">{item}</span>
        </li>
      ))}
    </ul>
  )
}

export default function FeedbackPage() {
  const router = useRouter()
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [name, setName] = useState('')

  useEffect(() => {
    const fb      = localStorage.getItem('probeiq_feedback')
    const session = localStorage.getItem('probeiq_session')
    if (!fb) { router.replace('/'); return }
    setFeedback(JSON.parse(fb))
    if (session) setName(JSON.parse(session).candidate.member.name)
  }, [router])

  function restart() {
    localStorage.removeItem('probeiq_session')
    localStorage.removeItem('probeiq_feedback')
    router.push('/')
  }

  if (!feedback) return null

  const cards = [
    {
      label:   'Summary',
      border:  'border-t-[#1E3A5F]',
      content: <p className="text-sm leading-relaxed text-[#0F172A]">{feedback.summary ?? '—'}</p>,
    },
    {
      label:   'Strengths',
      border:  'border-t-[#059669]',
      content: <List items={feedback.strengths} bulletColor="text-[#059669]" />,
    },
    {
      label:   'Areas to Improve',
      border:  'border-t-amber-500',
      content: <List items={feedback.gaps} bulletColor="text-amber-500" />,
    },
    {
      label:   'Next Steps',
      border:  'border-t-[#2563EB]',
      content: <List items={feedback.next} bulletColor="text-[#2563EB]" />,
    },
  ]

  return (
    <main className="min-h-dvh bg-[#F8FAFC] flex flex-col items-center px-4 py-10">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-[#1E3A5F]">Interview Complete</h1>
        <p className="text-slate-500 text-sm mt-1">Feedback for {name}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-3xl mb-8">
        {cards.map(c => (
          <div
            key={c.label}
            className={`bg-white rounded-xl border border-[#E4E7EB] border-t-4 ${c.border} p-5 shadow-sm`}
          >
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
              {c.label}
            </h3>
            {c.content}
          </div>
        ))}
      </div>

      <button
        onClick={restart}
        className="px-8 py-3 bg-[#1E3A5F] text-white font-semibold rounded-lg cursor-pointer
          transition-colors duration-150 hover:bg-[#16304f]"
      >
        ← New Interview
      </button>
    </main>
  )
}
