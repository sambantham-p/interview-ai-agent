//Provides centralized API error handling for mutation requests.
export function toErrorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback
}
