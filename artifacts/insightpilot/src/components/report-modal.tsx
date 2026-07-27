/**
 * InsightPilot — Report generation modal and download helper.
 *
 * Extracted from dashboard.tsx to keep the dashboard focused on data display.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';

export type ReportState = 'idle' | 'loading' | 'success' | 'error';

/** Trigger a PDF download from the /api/report endpoint. */
export async function downloadReport(datasetId: string): Promise<void> {
  const resp = await fetch('/api/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ datasetId }),
  });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Report generation failed (${resp.status})`);
  }
  const blob = await resp.blob();
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = 'InsightPilot_Executive_Report.pdf';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Animated modal shown during report generation, success, and error states. */
export function ReportModal({ state, error, onClose }: {
  state: ReportState;
  error: string | null;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {state !== 'idle' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.92, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.92, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="bg-card border border-border rounded-2xl shadow-2xl p-8 max-w-sm w-full mx-4 text-center"
          >
            {state === 'loading' && (
              <>
                <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Loader2 className="w-8 h-8 text-primary animate-spin" />
                </div>
                <h3 className="text-lg font-bold text-foreground mb-2">Generating Report</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  AI is preparing your Executive Report…
                </p>
                <div className="mt-5 w-full bg-muted rounded-full h-1.5 overflow-hidden">
                  <motion.div
                    className="h-full bg-primary rounded-full"
                    initial={{ width: '5%' }}
                    animate={{ width: '85%' }}
                    transition={{ duration: 8, ease: 'easeOut' }}
                  />
                </div>
              </>
            )}

            {state === 'success' && (
              <>
                <div className="w-16 h-16 bg-emerald-100 dark:bg-emerald-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 className="w-8 h-8 text-emerald-600 dark:text-emerald-400" />
                </div>
                <h3 className="text-lg font-bold text-foreground mb-2">Report Ready</h3>
                <p className="text-sm text-muted-foreground mb-5">
                  Your executive PDF has been downloaded.
                </p>
                <button
                  onClick={onClose}
                  className="px-6 py-2 bg-primary text-primary-foreground text-sm font-semibold rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Done
                </button>
              </>
            )}

            {state === 'error' && (
              <>
                <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                  <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
                </div>
                <h3 className="text-lg font-bold text-foreground mb-2">Report Failed</h3>
                <p className="text-sm text-muted-foreground mb-1">{error}</p>
                <p className="text-xs text-muted-foreground mb-5">Please try again.</p>
                <button
                  onClick={onClose}
                  className="px-6 py-2 bg-muted text-foreground text-sm font-semibold rounded-lg hover:bg-border transition-colors"
                >
                  Close
                </button>
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
