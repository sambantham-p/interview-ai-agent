import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { HealthCheck } from '../../types/api'

export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.get<HealthCheck>('/health'),
  })
}
