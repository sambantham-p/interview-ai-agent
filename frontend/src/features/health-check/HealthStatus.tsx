import { useHealthCheck } from './useHealthCheck'

// The one real (non-placeholder) piece of this scaffold — proves the full
// chain works end to end: Vite dev proxy -> FastAPI /api/v1/health ->
// response envelope unwrapped by lib/api.ts -> cached by TanStack Query.
export function HealthStatus() {
  const { data, isPending, isError, error } = useHealthCheck()

  if (isPending) {
    return <p className="text-sm text-slate-500">Checking backend…</p>
  }

  if (isError) {
    return (
      <p className="text-sm text-red-600">
        Backend unreachable: {error.message}
      </p>
    )
  }

  return (
    <p className="text-sm text-emerald-600">
      {data.service} is {data.health} ✓
    </p>
  )
}
