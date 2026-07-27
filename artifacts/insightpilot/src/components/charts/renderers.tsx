/**
 * InsightPilot — chart renderer components.
 *
 * Extracted from dashboard.tsx so the dashboard page stays focused on layout
 * and data orchestration rather than Recharts implementation details.
 *
 * Exports:
 *   ChartRenderer      — dispatcher that picks the right renderer by chart type
 *   RotatedTick        — angled X-axis tick for dense data
 *   FlatTick           — horizontal X-axis tick for sparse data
 */

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Cell, PieChart, Pie,
  Legend, ScatterChart, Scatter,
} from 'recharts';
import { HelpCircle } from 'lucide-react';
import type { ChartSpec } from '@workspace/api-client-react';
import {
  PALETTE, TOOLTIP_STYLE, Y_AXIS_STYLE,
  truncateLabel, formatYAxis,
  prepareBarData, preparePieData,
  needsRotation, xInterval,
} from '../../lib/chart-utils';

// ─── Custom ticks ──────────────────────────────────────────────────────────────

export function RotatedTick({ x, y, payload }: { x?: number; y?: number; payload?: { value: string } }) {
  const label = truncateLabel(String(payload?.value ?? ''), 15);
  return (
    <g transform={`translate(${x},${y})`}>
      <text
        x={0} y={0} dy={6}
        textAnchor="end"
        fill="hsl(var(--muted-foreground))"
        fontSize={10}
        fontFamily="inherit"
        transform="rotate(-38)"
      >
        {label}
      </text>
    </g>
  );
}

export function FlatTick({ x, y, payload }: { x?: number; y?: number; payload?: { value: string } }) {
  const label = truncateLabel(String(payload?.value ?? ''), 13);
  return (
    <g transform={`translate(${x},${y})`}>
      <text
        x={0} y={0} dy={14}
        textAnchor="middle"
        fill="hsl(var(--muted-foreground))"
        fontSize={10}
        fontFamily="inherit"
      >
        {label}
      </text>
    </g>
  );
}

// ─── Individual renderers ──────────────────────────────────────────────────────

function LineChartRenderer({ chart }: { chart: ChartSpec }) {
  const rotated      = needsRotation(chart.data);
  const bottomMargin = rotated ? 60 : 24;
  const interval     = xInterval(chart.data.length);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={chart.data} margin={{ top: 12, right: 20, left: 4, bottom: bottomMargin }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.5} />
        <XAxis
          dataKey="label"
          axisLine={false} tickLine={false}
          tick={rotated ? <RotatedTick /> : <FlatTick />}
          interval={interval}
        />
        <YAxis
          axisLine={false} tickLine={false}
          tick={Y_AXIS_STYLE}
          tickFormatter={formatYAxis}
          width={52}
        />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [formatYAxis(v), 'Value']} />
        <Line
          type="monotone"
          dataKey="value"
          stroke={PALETTE[0]}
          strokeWidth={2.5}
          dot={chart.data.length > 14 ? false : { r: 3.5, fill: PALETTE[0], strokeWidth: 0 }}
          activeDot={{ r: 5, strokeWidth: 0, fill: PALETTE[0] }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function BarChartRenderer({ chart }: { chart: ChartSpec }) {
  const prepared     = prepareBarData(chart.data);
  const rotated      = needsRotation(prepared);
  const bottomMargin = rotated ? 64 : 24;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={prepared}
        margin={{ top: 12, right: 20, left: 4, bottom: bottomMargin }}
        barCategoryGap="28%"
      >
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.5} />
        <XAxis
          dataKey="label"
          axisLine={false} tickLine={false}
          tick={rotated ? <RotatedTick /> : <FlatTick />}
          interval={0}
        />
        <YAxis
          axisLine={false} tickLine={false}
          tick={Y_AXIS_STYLE}
          tickFormatter={formatYAxis}
          width={52}
        />
        <Tooltip
          cursor={{ fill: 'hsl(var(--accent))', opacity: 0.6 }}
          {...TOOLTIP_STYLE}
          formatter={(v: number) => [formatYAxis(v), 'Value']}
        />
        <Bar dataKey="value" radius={[5, 5, 0, 0]} maxBarSize={52}>
          {prepared.map((_entry, i) => (
            <Cell key={`cell-${i}`} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function PieChartRenderer({ chart }: { chart: ChartSpec }) {
  const prepared = preparePieData(chart.data);

  const renderCustomLabel = ({
    cx, cy, midAngle, innerRadius, outerRadius, percent,
  }: {
    cx: number; cy: number; midAngle: number;
    innerRadius: number; outerRadius: number; percent: number;
  }) => {
    if (percent < 0.05) return null;
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.58;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return (
      <text
        x={x} y={y}
        fill="white"
        textAnchor="middle" dominantBaseline="central"
        fontSize={11} fontWeight={700} fontFamily="inherit"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
        <Pie
          data={prepared}
          dataKey="value" nameKey="label"
          cx="50%" cy="44%"
          outerRadius="60%" innerRadius="30%"
          paddingAngle={2}
          labelLine={false}
          label={renderCustomLabel}
        >
          {prepared.map((_entry, i) => (
            <Cell key={`cell-${i}`} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Pie>
        <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [formatYAxis(v), 'Value']} />
        <Legend
          iconType="circle" iconSize={7}
          wrapperStyle={{ fontSize: 11, paddingTop: 6, lineHeight: '20px' }}
          formatter={(value) => (
            <span style={{ color: 'hsl(var(--foreground))', opacity: 0.8 }}>
              {truncateLabel(String(value), 22)}
            </span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

function HistogramRenderer({ chart }: { chart: ChartSpec }) {
  const rotated      = needsRotation(chart.data);
  const bottomMargin = rotated ? 64 : 24;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={chart.data}
        margin={{ top: 12, right: 20, left: 4, bottom: bottomMargin }}
        barCategoryGap="4%"
      >
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.5} />
        <XAxis
          dataKey="label"
          axisLine={false} tickLine={false}
          tick={rotated ? <RotatedTick /> : <FlatTick />}
          interval={0}
        />
        <YAxis
          axisLine={false} tickLine={false}
          tick={Y_AXIS_STYLE}
          tickFormatter={formatYAxis}
          width={44}
          label={{ value: 'Frequency', angle: -90, position: 'insideLeft', offset: 12, style: { ...Y_AXIS_STYLE, fontSize: 9 } }}
        />
        <Tooltip
          {...TOOLTIP_STYLE}
          cursor={{ fill: 'hsl(var(--accent))', opacity: 0.6 }}
          formatter={(v: number) => [formatYAxis(v), 'Count']}
        />
        <Bar dataKey="value" fill={PALETTE[0]} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function ScatterRenderer({ chart }: { chart: ChartSpec }) {
  const scatterData = chart.data.map(d => ({
    x: parseFloat(String(d.label)) || 0,
    y: d.value,
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ScatterChart margin={{ top: 12, right: 20, left: 4, bottom: 24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
        <XAxis
          dataKey="x" type="number" name={chart.x}
          axisLine={false} tickLine={false}
          tick={Y_AXIS_STYLE} tickFormatter={formatYAxis}
          label={{ value: chart.x, position: 'insideBottom', offset: -10, style: { ...Y_AXIS_STYLE, fontSize: 10 } }}
        />
        <YAxis
          dataKey="y" type="number" name={chart.y}
          axisLine={false} tickLine={false}
          tick={Y_AXIS_STYLE} tickFormatter={formatYAxis}
          width={52}
        />
        <Tooltip cursor={{ strokeDasharray: '3 3' }} {...TOOLTIP_STYLE} formatter={(v: number) => [formatYAxis(v)]} />
        <Scatter data={scatterData} fill={PALETTE[0]} fillOpacity={0.6} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

// ─── Dispatcher ────────────────────────────────────────────────────────────────

export function ChartRenderer({ chart }: { chart: ChartSpec }) {
  if (!chart.data || chart.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-3">
        <HelpCircle className="w-9 h-9 opacity-30" />
        <p className="text-sm font-medium">No data available for this chart</p>
      </div>
    );
  }
  switch (chart.type) {
    case 'line':      return <LineChartRenderer chart={chart} />;
    case 'bar':       return <BarChartRenderer chart={chart} />;
    case 'pie':       return <PieChartRenderer chart={chart} />;
    case 'histogram': return <HistogramRenderer chart={chart} />;
    case 'scatter':   return <ScatterRenderer chart={chart} />;
    default:          return <BarChartRenderer chart={chart} />;
  }
}
