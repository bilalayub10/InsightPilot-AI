/**
 * InsightPilot — CEO Briefing Card
 *
 * Executive intelligence panel displayed at the top of the dashboard
 * immediately after dataset analysis completes. Generated entirely from
 * deterministic analytics — no LLM.
 */

import { motion } from 'framer-motion';
import { AlertTriangle, Lightbulb, Target, CheckCircle2 } from 'lucide-react';
import type { CeoBriefing } from '@workspace/api-client-react';

// ─── Health score badge ────────────────────────────────────────────────────────

function healthColor(score: number): { ring: string; fill: string; text: string; badge: string } {
  if (score >= 90) return {
    ring: 'stroke-emerald-500',
    fill: 'hsl(142 71% 45%)',
    text: 'text-emerald-600 dark:text-emerald-400',
    badge: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  };
  if (score >= 75) return {
    ring: 'stroke-blue-500',
    fill: 'hsl(221 83% 53%)',
    text: 'text-blue-600 dark:text-blue-400',
    badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  };
  if (score >= 60) return {
    ring: 'stroke-amber-400',
    fill: 'hsl(38 92% 50%)',
    text: 'text-amber-600 dark:text-amber-400',
    badge: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  };
  if (score >= 40) return {
    ring: 'stroke-orange-500',
    fill: 'hsl(25 95% 53%)',
    text: 'text-orange-600 dark:text-orange-400',
    badge: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  };
  return {
    ring: 'stroke-red-500',
    fill: 'hsl(0 84% 60%)',
    text: 'text-red-600 dark:text-red-400',
    badge: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };
}

function urgencyColors(urgency: string): string {
  switch (urgency) {
    case 'Critical': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800';
    case 'High':     return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 border border-orange-200 dark:border-orange-800';
    case 'Medium':   return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border border-amber-200 dark:border-amber-800';
    default:         return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800';
  }
}

function HealthScoreBadge({ score, status }: { score: number; status: string }) {
  const colors = healthColor(score);
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const progress = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-1.5 shrink-0">
      <div className="relative w-24 h-24">
        {/* Track */}
        <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 96 96">
          <circle
            cx="48" cy="48" r={radius}
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth="8"
          />
          <circle
            cx="48" cy="48" r={radius}
            fill="none"
            stroke={colors.fill}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={progress}
            style={{ transition: 'stroke-dashoffset 1.2s ease-out' }}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-2xl font-bold leading-none ${colors.text}`}>{score}</span>
          <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-widest mt-0.5">/ 100</span>
        </div>
      </div>
      <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${colors.badge}`}>
        {status}
      </span>
    </div>
  );
}

// ─── Info row ──────────────────────────────────────────────────────────────────

function InfoRow({
  icon: Icon,
  iconBg,
  iconColor,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  iconBg: string;
  iconColor: string;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center mt-0.5 ${iconBg}`}>
        <Icon className={`w-4 h-4 ${iconColor}`} />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-0.5">{label}</p>
        <p className="text-sm text-foreground leading-relaxed">{value}</p>
      </div>
    </div>
  );
}

// ─── Main component ────────────────────────────────────────────────────────────

export function CeoBriefingCard({ briefing }: { briefing: CeoBriefing }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="bg-card border border-border rounded-2xl shadow-sm overflow-hidden"
    >
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-gradient-to-r from-slate-900 to-slate-800 dark:from-slate-800 dark:to-slate-900 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-0.5">
            Executive Intelligence
          </p>
          <h2 className="text-lg font-bold text-white">CEO Briefing</h2>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex flex-col items-end">
            <p className="text-[10px] text-slate-400 uppercase tracking-widest font-medium mb-0.5">Domain</p>
            <p className="text-sm font-semibold text-white">{briefing.business_domain}</p>
          </div>
          <div className="h-6 w-px bg-slate-600 hidden sm:block" />
          <div className="flex flex-col items-end">
            <p className="text-[10px] text-slate-400 uppercase tracking-widest font-medium mb-0.5">Confidence</p>
            <p className="text-sm font-semibold text-white">{briefing.confidence}%</p>
          </div>
          <div className="h-6 w-px bg-slate-600 hidden sm:block" />
          <div className="flex flex-col items-end">
            <p className="text-[10px] text-slate-400 uppercase tracking-widest font-medium mb-0.5">Urgency</p>
            <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${urgencyColors(briefing.urgency)}`}>
              {briefing.urgency}
            </span>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-6 grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-8">

        {/* Left column: health score */}
        <div className="flex flex-col items-center gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground text-center mb-3">
              Overall Health
            </p>
            <HealthScoreBadge
              score={briefing.overall_health.score}
              status={briefing.overall_health.status}
            />
          </div>
        </div>

        {/* Right column: detail grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <InfoRow
            icon={AlertTriangle}
            iconBg="bg-red-100 dark:bg-red-900/30"
            iconColor="text-red-600 dark:text-red-400"
            label="Biggest Risk"
            value={briefing.biggest_risk}
          />
          <InfoRow
            icon={Lightbulb}
            iconBg="bg-amber-100 dark:bg-amber-900/30"
            iconColor="text-amber-600 dark:text-amber-400"
            label="Top Opportunity"
            value={briefing.top_opportunity}
          />
          <InfoRow
            icon={Target}
            iconBg="bg-blue-100 dark:bg-blue-900/30"
            iconColor="text-blue-600 dark:text-blue-400"
            label="Priority Action"
            value={briefing.priority_action}
          />
        </div>
      </div>

      {/* Executive Summary */}
      <div className="px-6 pb-5 border-t border-border/60 pt-5 mx-0">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">
          Executive Summary
        </p>
        <p className="text-sm text-foreground/85 leading-7">{briefing.executive_summary}</p>
      </div>

      {/* Key Takeaways */}
      <div className="px-6 pb-6 border-t border-border/60 pt-5">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-3">
          Key Takeaways
        </p>
        <div className="space-y-2.5">
          {briefing.key_takeaways.map((takeaway, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: 0.2 + i * 0.1 }}
              className="flex items-start gap-2.5"
            >
              <CheckCircle2 className="w-4 h-4 shrink-0 text-primary mt-0.5" />
              <p className="text-sm text-foreground/85 leading-relaxed">{takeaway}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
