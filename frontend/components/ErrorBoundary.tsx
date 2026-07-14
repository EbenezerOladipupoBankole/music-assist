import { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/** Catches render-time errors anywhere below it so a bug in one part of the
 * tree shows a recoverable message instead of a blank white screen. */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Music-Assist: Unhandled render error", error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-[100dvh] items-center justify-center bg-[#F8FAFC] px-6" role="alert">
          <div className="max-w-md text-center">
            <h1 className="font-serif text-2xl font-black text-slate-900 mb-3">Something went wrong</h1>
            <p className="text-sm text-slate-500 mb-6">
              Music Assist hit an unexpected error. Reloading the page usually fixes this.
            </p>
            <button
              onClick={this.handleReload}
              className="px-6 py-3 rounded-xl bg-slate-900 text-white text-xs font-black uppercase tracking-widest shadow-lg hover:bg-slate-800 transition-all"
            >
              Reload
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
