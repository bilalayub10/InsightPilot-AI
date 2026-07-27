/**
 * InsightPilot — AI Copilot suggested questions.
 *
 * Domain-specific question banks for the AI Copilot chat panel.
 * Extracted from ai-copilot.tsx so the suggestion data is co-located
 * with other lib constants rather than embedded in the UI component.
 */

export const GENERIC_SUGGESTIONS = [
  'Summarize this dataset',
  'What is the biggest business risk?',
  'Which KPI needs attention?',
  'Explain the anomalies',
  'What are the top opportunities?',
  'Recommended actions for management',
];

export const DOMAIN_SUGGESTIONS: Record<string, string[]> = {
  sales:              ['Why might revenue be declining?', 'Which product drives the most sales?', 'What does the sales pipeline look like?', 'Identify underperforming segments', 'What should the sales team focus on?', 'Forecast concerns for next quarter'],
  marketing:          ['Which channel has the best ROI?', 'What does campaign performance look like?', 'Where is customer acquisition cost highest?', 'Which audience segments convert best?', 'What marketing spend can be optimized?', 'Explain the conversion funnel'],
  finance:            ['What are the main cost drivers?', 'How does cash flow look?', 'Which expenses are out of control?', 'What is the profitability trend?', 'Where can we cut spending?', 'Explain budget variances'],
  hr:                 ['Why is employee attrition high?', 'What does headcount growth look like?', 'Which departments are understaffed?', 'What factors drive employee turnover?', 'How is workforce productivity trending?', 'What should HR focus on?'],
  telecommunications: ['Why is customer churn high?', 'What drives subscriber growth?', 'Which plans have the best retention?', 'Where is ARPU declining?', 'What churn risk factors exist?', 'How to improve customer lifetime value?'],
  saas:               ['What is the churn rate trend?', 'How is MRR growing?', 'Which cohort has the best retention?', 'What drives expansion revenue?', 'Where is NRR below benchmark?', 'What is causing ARR compression?'],
  healthcare:         ['What are the key patient outcome metrics?', 'Which departments have the most risk?', 'How are readmission rates trending?', 'What operational bottlenecks exist?', 'Explain patient satisfaction trends', 'Where should resources be prioritized?'],
  retail:             ['Which products have the highest margin?', 'What is the inventory turnover rate?', 'Which stores underperform?', 'What is driving returns?', 'How is basket size trending?', 'What seasonality patterns exist?'],
  ecommerce:          ['What is cart abandonment driven by?', 'Which acquisition channels convert best?', 'How is average order value trending?', 'What drives repeat purchases?', 'Which product categories are declining?', 'How to improve customer retention?'],
  operations:         ['Where are the biggest inefficiencies?', 'What is driving operational costs up?', 'Which processes need optimization?', 'How is throughput trending?', 'What bottlenecks exist?', 'Where should we invest in automation?'],
};

/** Return the 6 most relevant suggested questions for the given domain. */
export function getSuggestions(domain?: string): string[] {
  if (!domain) return GENERIC_SUGGESTIONS;
  const key = domain.toLowerCase().replace(/[_\s]/g, '');
  return (
    DOMAIN_SUGGESTIONS[domain.toLowerCase()] ??
    DOMAIN_SUGGESTIONS[key] ??
    GENERIC_SUGGESTIONS
  );
}
