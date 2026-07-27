import { ReactNode } from 'react';

interface ChartCardProps {
  title: string;
  children: ReactNode;
  description?: string;
  badge?: ReactNode;
  /** Optional content rendered below the chart area inside the card */
  footer?: ReactNode;
  /** Override min chart height (default 340px) */
  chartHeight?: number;
}

export function ChartCard({ title, children, description, badge, footer, chartHeight = 340 }: ChartCardProps) {
  return (
    <div className="
      flex flex-col bg-card border border-border rounded-2xl
      shadow-sm hover:shadow-md hover:-translate-y-0.5
      transition-all duration-200 h-full
    ">
      {/* Header */}
      <div className="px-5 pt-5 pb-4 border-b border-border/60">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="text-[13px] font-semibold text-foreground leading-snug line-clamp-2">
              {title}
            </h3>
            {description && (
              <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed line-clamp-2">
                {description}
              </p>
            )}
          </div>
          {badge && <div className="shrink-0 mt-0.5">{badge}</div>}
        </div>
      </div>

      {/* Chart area — fixed height keeps grid rows aligned */}
      <div className="px-3 py-4 flex-1" style={{ minHeight: chartHeight }}>
        {children}
      </div>

      {/* AI insight footer */}
      {footer && footer}
    </div>
  );
}
