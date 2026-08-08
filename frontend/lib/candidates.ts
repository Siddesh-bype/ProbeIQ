import type { Candidate } from './types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function getCandidates(): Promise<Candidate[]> {
  const response = await fetch(`${API_URL}/api/candidates`)
  if (!response.ok) {
    throw new Error('Failed to fetch candidates')
  }
  return response.json()
}

