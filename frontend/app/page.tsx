'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { CANDIDATES } from '@/lib/candidates'
import { startInterview } from '@/lib/api'

export default function HomePage() {
  const router = useRouter()
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleStart() {
    if (selectedIdx === null) return
    setLoading(true)
    setError(null)
    const candidate = CANDIDATES[selectedIdx]
    const sessionId = crypto.randomUUID()

    try {
      const data = await startInterview(sessionId, candidate)
      localStorage.setItem(
        'probeiq_session',
        JSON.stringify({ sessionId, candidate, messages: [{ role: 'interviewer', text: data.reply }] }),
      )
      router.push('/interview')
    } catch (e) {
      setError('Cannot connect to backend. Make sure the server is running on port 8000.')
      setLoading(false)
    }
  }

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center p-4
      bg-gradient-to-br from-slate-900 via-[#1E3A5F] to-blue-800">

      <div className="mb-1 text-2xl font-bold text-white tracking-tight">⬡ ProbeIQ</div>
      <p className="text-slate-400 text-sm mb-10">AI-powered technical interview agent</p>

      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
        <h2 className="text-xs font-semibold text-[#1E3A5F] uppercase tracking-widest mb-4">
          Select a Candidate
        </h2>

        <div className="flex flex-col gap-3 mb-6">
          {CANDIDATES.map((c, i) => (
            <button
              key={c.member.id}
              onClick={() => setSelectedIdx(i)}
              className={`flex justify-between items-center p-4 rounded-lg border-2 text-left
                cursor-pointer transition-all duration-150
                ${selectedIdx === i
                  ? 'border-[#2563EB] bg-blue-50'
                  : 'border-[#E4E7EB] hover:border-[#2563EB] hover:bg-blue-50'}`}
            >
              <div>
                <div className="font-semibold text-sm text-[#0F172A]">{c.member.name}</div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {c.member.jobRole} · {c.member.yearsExperience}y exp · {c.member.education}
                </div>
              </div>
              <span className="ml-3 shrink-0 text-xs font-medium bg-blue-100 text-blue-700
                px-2.5 py-1 rounded-full">
                {c.signals.missionsCompleted} missions
              </span>
            </button>
          ))}
        </div>

        {error && (
          <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            {error}
          </p>
        )}

        <button
          onClick={handleStart}
          disabled={selectedIdx === null || loading}
          className="w-full py-3 bg-[#1E3A5F] text-white font-semibold rounded-lg
            transition-all duration-150 cursor-pointer
            disabled:opacity-40 disabled:cursor-not-allowed
            hover:bg-[#16304f] active:scale-[0.98]"
        >
          {loading ? 'Starting…' : 'Start Interview →'}
        </button>
      </div>
    </main>
  )
}
