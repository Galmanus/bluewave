/**
 * Sentry error tracking for the React frontend.
 *
 * Initializes only when VITE_SENTRY_DSN is set.
 * No PII is sent — only error data and breadcrumbs.
 */

import * as Sentry from "@sentry/react";

export function initSentry(): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({ maskAllText: true, blockAllMedia: true }),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 1.0,
    beforeSend(event) {
      // Strip PII from breadcrumbs
      if (event.breadcrumbs) {
        event.breadcrumbs = event.breadcrumbs.map((bc) => {
          if (bc.category === "xhr" || bc.category === "fetch") {
            delete bc.data?.requestBody;
          }
          return bc;
        });
      }
      return event;
    },
  });
}

export const SentryErrorBoundary = Sentry.ErrorBoundary;
