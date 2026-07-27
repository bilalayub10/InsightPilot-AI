/**
 * KpiCard — executive-grade metric tile.
 *
 * Smart value formatting: detects currency, percentages, and large
 * numbers (K / M / B) so the backend's raw string is always rendered
 * in the most readable form.  No fake trend percentages are shown.
 */

import {
  DollarSign, Users, ShoppingCart, TrendingUp, UserMinus, Package,
  Star, Briefcase, MessageSquare, MousePointerClick, CreditCard,
  BarChart2, Activity, Layers, Heart, BookOpen, Zap, Globe,
} from 'lucide-react';
import { type LucideIcon } from 'lucide-react';
import { KpiMetric } from '@workspace/api-client-react';

interface KpiCardProps {
  metric: KpiMetric;
}

// ─── Smart value formatter ──────────────────────────────────────────────────

function formatValue(raw: string): string {
  const s = raw.trim();
  if (!s) return '—';

  // Already percentage
  if (s.endsWith('%')) {
    const n = parseFloat(s);
    if (!isNaN(n)) return `${n % 1 === 0 ? n.toFixed(0) : parseFloat(n.toFixed(1))}%`;
    return s;
  }

  // Detect leading currency symbol
  const currMatch = s.match(/^([^\d\s.,\-])/);
  const prefix = currMatch ? currMatch[1] : '';
  const numStr = s.replace(/[^0-9.\-]/g, '');
  const n = parseFloat(numStr);

  if (!isNaN(n) && numStr !== '') {
    const abs = Math.abs(n);
    if (abs >= 1_000_000_000) return `${prefix}${(n / 1_000_000_000).toFixed(1).replace(/\.0$/, '')}B`;
    if (abs >= 1_000_000)     return `${prefix}${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`;
    if (abs >= 10_000)        return `${prefix}${(n / 1_000).toFixed(1).replace(/\.0$/, '')}K`;
    if (abs >= 1_000)         return `${prefix}${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    if (abs < 10 && !prefix)  return `${parseFloat(n.toFixed(2))}`;
    return `${prefix}${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  }

  return s;
}

// ─── Icon & colour mapping ──────────────────────────────────────────────────

interface KpiStyle {
  Icon: LucideIcon;
  bg: string;
  text: string;
  border: string;
}

function resolveStyle(label: string): KpiStyle {
  const l = label.toLowerCase();

  if (/revenue|sales|income|turnover|earning|gross|net_income/.test(l))
    return { Icon: DollarSign, bg: 'bg-blue-50 dark:bg-blue-950/40', text: 'text-blue-600 dark:text-blue-400', border: 'border-blue-100 dark:border-blue-900/50' };
  if (/profit|margin|roi|roas|return/.test(l))
    return { Icon: TrendingUp, bg: 'bg-emerald-50 dark:bg-emerald-950/40', text: 'text-emerald-600 dark:text-emerald-400', border: 'border-emerald-100 dark:border-emerald-900/50' };
  if (/customer|client|user|member|visitor|guest|account/.test(l))
    return { Icon: Users, bg: 'bg-violet-50 dark:bg-violet-950/40', text: 'text-violet-600 dark:text-violet-400', border: 'border-violet-100 dark:border-violet-900/50' };
  if (/order|purchase|transaction|booking|deal/.test(l))
    return { Icon: ShoppingCart, bg: 'bg-indigo-50 dark:bg-indigo-950/40', text: 'text-indigo-600 dark:text-indigo-400', border: 'border-indigo-100 dark:border-indigo-900/50' };
  if (/attrition|churn|turnover|resign|quit|departure/.test(l))
    return { Icon: UserMinus, bg: 'bg-red-50 dark:bg-red-950/40', text: 'text-red-600 dark:text-red-400', border: 'border-red-100 dark:border-red-900/50' };
  if (/stock|inventory|item|sku|product|quantity|warehouse/.test(l))
    return { Icon: Package, bg: 'bg-amber-50 dark:bg-amber-950/40', text: 'text-amber-600 dark:text-amber-400', border: 'border-amber-100 dark:border-amber-900/50' };
  if (/score|rating|nps|csat|satisfaction|gpa|grade/.test(l))
    return { Icon: Star, bg: 'bg-yellow-50 dark:bg-yellow-950/40', text: 'text-yellow-600 dark:text-yellow-400', border: 'border-yellow-100 dark:border-yellow-900/50' };
  if (/employee|staff|headcount|workforce|fte|hire/.test(l))
    return { Icon: Briefcase, bg: 'bg-slate-100 dark:bg-slate-800/60', text: 'text-slate-600 dark:text-slate-400', border: 'border-slate-200 dark:border-slate-700/50' };
  if (/ticket|case|issue|support|complaint/.test(l))
    return { Icon: MessageSquare, bg: 'bg-cyan-50 dark:bg-cyan-950/40', text: 'text-cyan-600 dark:text-cyan-400', border: 'border-cyan-100 dark:border-cyan-900/50' };
  if (/campaign|click|impression|conversion|lead/.test(l))
    return { Icon: MousePointerClick, bg: 'bg-fuchsia-50 dark:bg-fuchsia-950/40', text: 'text-fuchsia-600 dark:text-fuchsia-400', border: 'border-fuchsia-100 dark:border-fuchsia-900/50' };
  if (/cost|expense|spend|budget|expenditure/.test(l))
    return { Icon: CreditCard, bg: 'bg-orange-50 dark:bg-orange-950/40', text: 'text-orange-600 dark:text-orange-400', border: 'border-orange-100 dark:border-orange-900/50' };
  if (/patient|admission|los|readmission/.test(l))
    return { Icon: Heart, bg: 'bg-rose-50 dark:bg-rose-950/40', text: 'text-rose-600 dark:text-rose-400', border: 'border-rose-100 dark:border-rose-900/50' };
  if (/student|enrollment|course|grade|gpa/.test(l))
    return { Icon: BookOpen, bg: 'bg-teal-50 dark:bg-teal-950/40', text: 'text-teal-600 dark:text-teal-400', border: 'border-teal-100 dark:border-teal-900/50' };
  if (/energy|power|kwh|usage|consumption/.test(l))
    return { Icon: Zap, bg: 'bg-lime-50 dark:bg-lime-950/40', text: 'text-lime-600 dark:text-lime-400', border: 'border-lime-100 dark:border-lime-900/50' };
  if (/session|pageview|mau|dau|mrr|arr|ltv/.test(l))
    return { Icon: Activity, bg: 'bg-pink-50 dark:bg-pink-950/40', text: 'text-pink-600 dark:text-pink-400', border: 'border-pink-100 dark:border-pink-900/50' };
  if (/shipment|freight|delivery|supply|logistics/.test(l))
    return { Icon: Globe, bg: 'bg-sky-50 dark:bg-sky-950/40', text: 'text-sky-600 dark:text-sky-400', border: 'border-sky-100 dark:border-sky-900/50' };
  if (/layer|tier|level|category|segment/.test(l))
    return { Icon: Layers, bg: 'bg-neutral-100 dark:bg-neutral-800', text: 'text-neutral-600 dark:text-neutral-400', border: 'border-neutral-200 dark:border-neutral-700/50' };

  return { Icon: BarChart2, bg: 'bg-primary/8', text: 'text-primary', border: 'border-primary/10' };
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function KpiCard({ metric }: KpiCardProps) {
  const { Icon, bg, text, border } = resolveStyle(metric.label);
  const displayValue = formatValue(metric.value);

  return (
    <div className="
      group relative flex flex-col
      p-5 bg-card border border-border rounded-2xl
      shadow-sm hover:shadow-md hover:-translate-y-0.5
      transition-all duration-200 cursor-default
      min-h-[130px]
    ">
      {/* Top row: icon + label */}
      <div className="flex items-center justify-between mb-4">
        <div className={`inline-flex items-center justify-center w-9 h-9 rounded-xl ${bg} ${border} border`}>
          <Icon className={`w-4 h-4 ${text}`} />
        </div>
      </div>

      {/* Label */}
      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 truncate leading-none">
        {metric.label}
      </p>

      {/* Value */}
      <p className={`text-2xl font-bold leading-none tracking-tight ${
        displayValue.length > 9 ? 'text-xl' : ''
      } text-foreground`}>
        {displayValue}
      </p>

      {/* Decorative corner tint */}
      <div className={`absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none bg-gradient-to-br from-transparent to-${bg.replace('bg-', '')}/30`} />
    </div>
  );
}
