/**
 * Sentry error tracking stub.
 * Sentry is optional — only active when @sentry/react is installed and VITE_SENTRY_DSN is set.
 */

export function initSentry(): void {
  // Sentry disabled — no DSN configured
}

export function SentryErrorBoundary({ children }: { children: React.ReactNode }) {
  return children as any;
}
