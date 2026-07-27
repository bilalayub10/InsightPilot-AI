/**
 * InsightPilot — chart utility constants and pure helpers.
 *
 * Extracted from dashboard.tsx so chart renderers and the dashboard page
 * can both import from a single source of truth.
 */

import type { ChartDataPoint } from '@workspace/api-client-react';

// ─── Palette ───────────────────────────────────────────────────────────────────

export const PALETTE = [
  'hsl(221 83% 53%)',   // primary blue
  'hsl(199 89% 48%)',   // cyan
  'hsl(262 52% 60%)',   // violet
  'hsl(142 71% 45%)',   // green
  'hsl(38 92% 50%)',    // amber
  'hsl(346 77% 56%)',   // rose
  'hsl(186 100% 38%)',  // teal
  'hsl(316 60% 56%)',   // pink
];

// ─── Recharts shared style objects ─────────────────────────────────────────────

export const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: 'hsl(var(--card))',
    borderRadius: '10px',
    border: '1px solid hsl(var(--border))',
    boxShadow: '0 8px 24px rgb(0 0 0 / 0.12)',
    fontSize: '13px',
  },
  itemStyle: { color: 'hsl(var(--foreground))', fontWeight: 600 },
  labelStyle: { color: 'hsl(var(--muted-foreground))', fontWeight: 400 },
};

export const Y_AXIS_STYLE = {
  fill: 'hsl(var(--muted-foreground))',
  fontSize: 11,
};

// ─── Label helpers ─────────────────────────────────────────────────────────────

/** Truncate a label string to maxLen characters. */
export function truncateLabel(s: string, maxLen = 14): string {
  const str = String(s ?? '');
  return str.length > maxLen ? str.slice(0, maxLen - 1) + '…' : str;
}

/** Format Y-axis numbers with K / M / B suffixes. */
export function formatYAxis(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1).replace(/\.0$/, '')}B`;
  if (abs >= 1_000_000)     return `${(value / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`;
  if (abs >= 10_000)        return `${(value / 1_000).toFixed(1).replace(/\.0$/, '')}K`;
  if (abs >= 1_000)         return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return value % 1 === 0 ? String(value) : parseFloat(value.toFixed(2)).toString();
}

// ─── Data preparation ──────────────────────────────────────────────────────────

/** Sort descending, keep top N, collapse the rest as "Other". */
export function prepareBarData(data: ChartDataPoint[], maxItems = 10): ChartDataPoint[] {
  const sorted = [...data].sort((a, b) => b.value - a.value);
  if (sorted.length <= maxItems) return sorted;
  const top        = sorted.slice(0, maxItems);
  const otherValue = sorted.slice(maxItems).reduce((sum, d) => sum + d.value, 0);
  return [...top, { label: 'Other', value: otherValue }];
}

/** Keep top 8 slices, collapse rest into "Other". */
export function preparePieData(data: ChartDataPoint[], maxSlices = 8): ChartDataPoint[] {
  const sorted = [...data].sort((a, b) => b.value - a.value);
  if (sorted.length <= maxSlices) return sorted;
  const top        = sorted.slice(0, maxSlices);
  const otherValue = sorted.slice(maxSlices).reduce((sum, d) => sum + d.value, 0);
  return [...top, { label: 'Other', value: otherValue }];
}

// ─── Axis helpers ──────────────────────────────────────────────────────────────

/**
 * Decide whether to rotate X-axis labels.
 * Rotates when there are many items OR labels are genuinely long.
 */
export function needsRotation(data: ChartDataPoint[]): boolean {
  if (data.length === 0) return false;
  if (data.length > 7) return true;
  const avgLen = data.reduce((sum, d) => sum + String(d.label ?? '').length, 0) / data.length;
  return avgLen > 9;
}

/** Optimal X-axis tick interval to avoid crowding. */
export function xInterval(count: number): number | 'preserveStartEnd' {
  if (count <= 12) return 0;
  if (count <= 30) return Math.ceil(count / 8) - 1;
  return 'preserveStartEnd';
}
