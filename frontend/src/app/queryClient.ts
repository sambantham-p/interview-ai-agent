import { QueryClient } from '@tanstack/react-query'
import { ApiRequestError } from '../lib/api'

const UNAUTHORIZED_STATUS = 401

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // A rejected session won't succeed on retry; the auth handler is
      // already signing the user out.
      retry: (failureCount, error) =>
        !(error instanceof ApiRequestError && error.statusCode === UNAUTHORIZED_STATUS) &&
        failureCount < 1,
      staleTime: 30_000,
    },
  },
})
