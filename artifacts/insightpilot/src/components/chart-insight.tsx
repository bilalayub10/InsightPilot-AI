/**
 * ChartInsightPanel — AI-generated chart explanation below a chart.
 */

import { motion } from 'framer-motion';
import { Sparkles, AlertCircle, Target } from 'lucide-react';
import type { ChartInsight } from '@workspace/api-client-react';

interface ChartInsightPanelProps {
  insight: ChartInsight;
}

function ConfidencePill({ value }: { value: number }) {
  const cls =
    value >= 75
      ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
      : value >= 55
      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
      : value >= 35
      ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
      : 'bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400';
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap ${cls}`}>
      {value}% confidence
    </span>
  );
}

export function ChartInsightPanel({ insight }: ChartInsightPanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, delay: 0.15 }}
      className="border-t border-border/60 bg-accent/20 px-5 py-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
            <Sparkles className="w-3 h-3 text-primary" />
          </div>
          <span className="text-[10px] font-semibold uppercase tracking-widest text-primary/70">AI Insight</span>
          {insight.title && (
            <span className="text-[11px] text-muted-foreground hidden sm:inline truncate max-w-[200px]">
              — {insight.title}
            </span>
          )}
        </div>
        <ConfidencePill value={insight.confidence} />
      </div>

      {/* Summary */}
      {insight.summary && (
        <p className="text-[12px] leading-relaxed text-foreground/75 mb-3 pl-7">
          {insight.summary}
        </p>
      )}

      {/* Impact + Recommendation in two columns on wide screens */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-0">
        {insight.business_impact && (
          <div className="flex items-start gap-2.5">
            <div className="shrink-0 mt-0.5 w-5 h-5 rounded-md flex items-center justify-center bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400">
              <AlertCircle className="w-3 h-3" />
            </div>
            <div className="min-w-0">
              <p className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground mb-0.5">Business Impact</p>
              <p className="text-[12px] leading-relaxed text-foreground/80">{insight.business_impact}</p>
            </div>
          </div>
        )}
        {insight.recommendation && (
          <div className="flex items-start gap-2.5">
            <div className="shrink-0 mt-0.5 w-5 h-5 rounded-md flex items-center justify-center bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400">
              <Target className="w-3 h-3" />
            </div>
            <div className="min-w-0">
              <p className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground mb-0.5">Recommendation</p>
              <p className="text-[12px] leading-relaxed text-foreground/80">{insight.recommendation}</p>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
