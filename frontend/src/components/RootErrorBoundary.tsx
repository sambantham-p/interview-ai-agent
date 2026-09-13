import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
}

// Root-level fallback only — catches render-time crashes anywhere below it
// and shows a generic message instead of a blank page. Feature-level
// boundaries (e.g. around interview-chat/) should be added once that page
// exists, so a crash there doesn't wipe an in-progress interview session —
// see frontend/README.md's "Error handling & logging" section.
export class RootErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Unhandled render error', error, info.componentStack)
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="mx-auto max-w-2xl p-8 text-center">
          <p className="text-lg font-semibold text-red-600">
            Something went wrong.
          </p>
          <p className="mt-2 text-slate-600">Please reload the page.</p>
        </div>
      )
    }
    return this.props.children
  }
}
