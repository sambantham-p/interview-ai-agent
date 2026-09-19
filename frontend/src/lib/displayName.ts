import type { User } from '../types/auth'


export function getDisplayName(user: Pick<User, 'name' | 'preferred_name'>): string {
  const preferred = user.preferred_name?.trim()
  if (preferred) return preferred
  return user.name.trim().split(/\s+/)[0] ?? ''
}
