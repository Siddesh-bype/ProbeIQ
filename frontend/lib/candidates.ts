import type { Candidate } from './types'

export const CANDIDATES: Candidate[] = [
  {
    member: { id: 'c1', name: 'Alex Chen', jobRole: 'ML Engineer', yearsExperience: 2, education: 'BS Computer Science', status: 'active' },
    missions: [
      { day: 2, attempts: 1, passed: true,  skipped: false },
      { day: 3, attempts: 2, passed: true,  skipped: false },
      { day: 4, attempts: 4, passed: true,  skipped: false },
      { day: 5, attempts: 1, passed: false, skipped: true  },
      { day: 6, attempts: 3, passed: true,  skipped: false },
    ],
    signals: { commitDays: 15, missionsCompleted: 4, missionsFirstTry: 2 },
  },
  {
    member: { id: 'c2', name: 'Priya Nair', jobRole: 'AI Engineer', yearsExperience: 3, education: 'MS Data Science', status: 'active' },
    missions: [
      { day: 1, attempts: 1, passed: true,  skipped: false },
      { day: 2, attempts: 1, passed: true,  skipped: false },
      { day: 3, attempts: 2, passed: true,  skipped: false },
      { day: 4, attempts: 1, passed: true,  skipped: false },
      { day: 5, attempts: 3, passed: true,  skipped: false },
      { day: 6, attempts: 2, passed: true,  skipped: false },
    ],
    signals: { commitDays: 22, missionsCompleted: 6, missionsFirstTry: 4 },
  },
  {
    member: { id: 'c3', name: 'Jordan Kim', jobRole: 'Full-Stack Dev', yearsExperience: 1, education: 'Bootcamp Graduate', status: 'active' },
    missions: [
      { day: 2, attempts: 3, passed: true,  skipped: false },
      { day: 3, attempts: 1, passed: false, skipped: true  },
      { day: 5, attempts: 2, passed: true,  skipped: false },
      { day: 7, attempts: 5, passed: true,  skipped: false },
    ],
    signals: { commitDays: 9, missionsCompleted: 3, missionsFirstTry: 1 },
  },
]
