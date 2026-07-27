/**
 * InsightPilot — Executive Dashboard
 *
 * Renders KPI cards, dynamic charts, and actionable insights from the
 * ChartPlanner + AnalyticsService pipeline.  All data is live from the
 * backend — nothing is hardcoded.
 *
 * Chart rendering logic lives in components/charts/renderers.tsx.
 * Chart utilities (palette, formatters, data helpers) live in lib/chart-utils.ts.
 * Report modal + download helper live in components/report-modal.tsx.
 */

import { useState } from 'react';
import { useAppStore } from '../store';
import { Layout } from '../components/layout';
import { KpiCard } from '../components/kpi-card';
import { ChartCard } from '../components/chart-card';
import { AICopilot } from '../components/ai-copilot';
import { CeoBriefingCard } from '../components/ceo-briefing';
import { ChartInsightPanel } from '../components/chart-insight';
import { ChartRenderer } from '../components/charts/renderers';
import { ReportModal, downloadReport, type ReportState } from '../components/report-modal';
import { useGetHealth, getGetHealthQueryKey } from '@workspace/api-client-react';
import { Link } from 'wouter';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, FileText, Calendar, Upload, HelpCircle,
  Lightbulb, TrendingUp, AlertTriangle, ShieldCheck, Info,
  Download, Loader2,
} from 'lucide-react';

// ─── Page-specific UI helpers ──────────────────────────────────────────────────

/** Renders the summary text with numbers bolded for quick scanning. */
function FormattedSummary({ text }: { text: string }) {
  const parts = text.split(/(\$?\b\d[\d,]*(?:\.\d+)?\s*(?:[KMB%]|rows?|columns?|values?)?(?=\b|[.,\s)]|$))/gi);
  return (
    <span className="text-[15px] leading-7 text-foreground/85">
      {parts.map((part, i) =>
        /^\$?\d/.test(part)
          ? <strong key={i} className="text-foreground font-semibold">{part}</strong>
          : part
      )}
    </span>
  );
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const cls =
    pct >= 75
      ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
      : pct >= 50
      ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
      : 'bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400';
  return (
    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap ${cls}`}>
      {pct}% match
    </span>
  );
}

const INSIGHT_CONFIGS = [
  { Icon: Lightbulb,    bg: 'bg-amber-100 dark:bg-amber-900/30',   text: 'text-amber-600 dark:text-amber-400'   },
  { Icon: TrendingUp,   bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-600 dark:text-emerald-400' },
  { Icon: AlertTriangle,bg: 'bg-orange-100 dark:bg-orange-900/30',  text: 'text-orange-600 dark:text-orange-400' },
  { Icon: ShieldCheck,  bg: 'bg-blue-100 dark:bg-blue-900/30',     text: 'text-blue-600 dark:text-blue-400'     },
  { Icon: Info,         bg: 'bg-violet-100 dark:bg-violet-900/30', text: 'text-violet-600 dark:text-violet-400' },
] as const;

// ─── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { analysisResult } = useAppStore();
  const { data: healthData } = useGetHealth({
    query: { enabled: true, queryKey: getGetHealthQueryKey() },
  });

  const [reportState, setReportState] = useState<ReportState>('idle');
  const [reportError, setReportError]  = useState<string | null>(null);

  const handleGenerateReport = async () => {
    if (!analysisResult) return;
    setReportState('loading');
    setReportError(null);
    try {
      await downloadReport(analysisResult.datasetId);
      setReportState('success');
    } catch (err) {
      setReportError(err instanceof Error ? err.message : 'An unexpected error occurred.');
      setReportState('error');
    }
  };

  // ── Empty state ──────────────────────────────────────────────────────────────
  if (!analysisResult) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center py-24 text-center px-4">
          <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center text-primary mb-6 shadow-sm">
            <Sparkles className="w-9 h-9" />
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-3">No active dataset</h2>
          <p className="text-muted-foreground max-w-md mb-8 leading-relaxed">
            Upload a CSV or Excel file and InsightPilot will automatically classify your data,
            compute KPIs, and generate domain-aware charts.
          </p>
          <Link
            href="/upload"
            className="px-6 py-3 bg-primary text-primary-foreground font-semibold rounded-xl hover:bg-primary/90 transition-all shadow-sm hover:shadow inline-flex items-center gap-2"
          >
            <Upload className="w-4 h-4" /> Upload Dataset
          </Link>
          {healthData && (
            <p className="text-xs text-muted-foreground mt-12 opacity-60">
              {healthData.service} v{healthData.version} · {healthData.status}
            </p>
          )}
        </div>
      </Layout>
    );
  }

  const charts     = analysisResult.charts ?? [];
  const analyzedAt = new Date(analysisResult.analyzedAt).toLocaleString(undefined, {
    dateStyle: 'medium', timeStyle: 'short',
  });

  return (
    <Layout>
      <div className="space-y-10 pb-14 max-w-[1400px]">

        {/* ── Page header ─────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col md:flex-row md:items-end justify-between gap-4"
        >
          <div>
            <h1 className="text-3xl font-bold text-foreground tracking-tight mb-2">
              Executive Dashboard
            </h1>
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-medium">
              <span className="flex items-center gap-1.5 bg-accent px-2.5 py-1.5 rounded-lg">
                <FileText className="w-3.5 h-3.5" />
                {analysisResult.datasetId}
              </span>
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                {analyzedAt}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3 self-start md:self-auto">
            <button
              onClick={handleGenerateReport}
              disabled={reportState === 'loading'}
              className={`px-4 py-2 text-sm font-semibold rounded-lg shadow-sm transition-all flex items-center gap-2 ${
                reportState === 'loading'
                  ? 'bg-muted text-muted-foreground cursor-not-allowed'
                  : 'bg-primary text-primary-foreground hover:bg-primary/90 hover:shadow'
              }`}
            >
              {reportState === 'loading'
                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                : <Download className="w-3.5 h-3.5" />
              }
              Generate Report
            </button>
            <Link
              href="/upload"
              className="px-4 py-2 bg-sidebar text-sidebar-foreground text-sm font-medium rounded-lg hover:opacity-90 transition-opacity shadow-sm"
            >
              Analyze New File
            </Link>
          </div>
        </motion.div>

        {/* ── CEO Briefing ─────────────────────────────────────────────────── */}
        {analysisResult.ceoBriefing && (
          <CeoBriefingCard briefing={analysisResult.ceoBriefing} />
        )}

        {/* ── Executive Summary ────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.05 }}
          className="relative overflow-hidden bg-gradient-to-br from-primary/[0.07] to-primary/[0.03] border border-primary/20 rounded-2xl p-7"
        >
          <div className="absolute left-0 top-0 h-full w-1 bg-primary rounded-l-2xl" />
          <div className="flex gap-5 ml-3">
            <div className="shrink-0 mt-0.5">
              <div className="w-9 h-9 bg-primary text-primary-foreground rounded-xl flex items-center justify-center shadow-sm">
                <Sparkles className="w-[18px] h-[18px]" />
              </div>
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-primary/70 mb-1.5">
                AI Executive Summary
              </p>
              <FormattedSummary text={analysisResult.summary} />
            </div>
          </div>
        </motion.div>

        {/* ── KPI cards ────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {analysisResult.kpis.map((kpi, idx) => (
            <motion.div
              key={kpi.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.08 + idx * 0.05 }}
            >
              <KpiCard metric={kpi} />
            </motion.div>
          ))}
        </div>

        {/* ── Charts ───────────────────────────────────────────────────────── */}
        {charts.length > 0 ? (
          <div className="grid gap-5 grid-cols-1 lg:grid-cols-2">
            {charts.map((chart, idx) => (
              <motion.div
                key={`${chart.title}-${idx}`}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.2 + idx * 0.08 }}
                className="h-full"
              >
                <ChartCard
                  title={chart.title}
                  description={chart.business_question}
                  badge={<ConfidenceBadge confidence={chart.confidence} />}
                  chartHeight={360}
                  footer={chart.insight ? <ChartInsightPanel insight={chart.insight} /> : undefined}
                >
                  <ChartRenderer chart={chart} />
                </ChartCard>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-border bg-card p-14 text-center text-muted-foreground shadow-sm">
            <HelpCircle className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p className="font-semibold">No charts could be generated for this dataset</p>
            <p className="text-sm mt-1 opacity-70">
              Try uploading a dataset with at least one numeric and one categorical column.
            </p>
          </div>
        )}

        {/* ── Insights panel ───────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.6 }}
          className="bg-card border border-border rounded-2xl shadow-sm overflow-hidden"
        >
          <div className="px-6 py-5 border-b border-border bg-accent/30">
            <h3 className="text-base font-semibold text-foreground">Actionable Insights</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              AI-generated findings based on detected patterns, anomalies and data quality signals.
            </p>
          </div>
          <div className="divide-y divide-border/60">
            {analysisResult.insights.map((insight, idx) => {
              const cfg = INSIGHT_CONFIGS[idx % INSIGHT_CONFIGS.length];
              return (
                <div
                  key={idx}
                  className="flex items-start gap-4 px-6 py-5 hover:bg-accent/40 transition-colors"
                >
                  <div className={`shrink-0 w-9 h-9 rounded-xl flex items-center justify-center ${cfg.bg} ${cfg.text}`}>
                    <cfg.Icon className="w-4 h-4" />
                  </div>
                  <p className="text-sm text-foreground leading-relaxed pt-1.5">{insight}</p>
                </div>
              );
            })}
          </div>
        </motion.div>

        {/* ── AI Copilot ───────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.75 }}
        >
          <AICopilot datasetId={analysisResult.datasetId} domain={analysisResult.domain} />
        </motion.div>

      </div>

      <ReportModal
        state={reportState}
        error={reportError}
        onClose={() => setReportState('idle')}
      />
    </Layout>
  );
}
