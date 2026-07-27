"""
InsightPilot AI — Business Domain Classifier (v2).

Detects the business domain of an uploaded dataset using only its column names.
No machine learning, no external APIs — purely deterministic, weighted keyword matching.

Public API (unchanged):
    BusinessClassifier.classify(column_names: list[str]) -> dict

Architecture
------------
1. Tokenise every column name into normalised lowercase tokens, handling
   camelCase, PascalCase, snake_case, hyphens, spaces, and acronyms.

2. Score every domain using a four-tier keyword registry:
      High-priority   → +5 pts  (industry-exclusive terms: "churn", "diagnosis", "invoice")
      Medium-priority → +3 pts  (domain-specific but shared: "service", "salary", "ticket")
      Low-priority    → +1 pt   (generic context: "customer", "date", "status")
      Negative        → −3 pts  (strong evidence of a *different* domain)

3. Compute a composite confidence score from three sub-scores:
      • weighted_score  — raw domain score normalised by the best achievable score
      • coverage_score  — fraction of dataset columns that matched any keyword
      • specificity_score — proportion of score coming from high+medium keywords

4. Return the winning domain if composite confidence ≥ MIN_CONFIDENCE_THRESHOLD,
   otherwise return "generic".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Composite score (0–1) required to claim a domain.  Below this → "generic".
MIN_CONFIDENCE_THRESHOLD = 0.40

# How many runner-up candidates to include in the response.
TOP_N_CANDIDATES = 5

# Scoring weights (integer points per matched token tier)
HIGH_WEIGHT    = 5
MEDIUM_WEIGHT  = 3
LOW_WEIGHT     = 1
NEGATIVE_WEIGHT = -3   # applied as a penalty

# Composite score weights — must sum to 1.0
W_SCORE       = 0.55   # weighted keyword score
W_COVERAGE    = 0.25   # fraction of columns matched
W_SPECIFICITY = 0.20   # fraction of score from high+medium keywords


# ---------------------------------------------------------------------------
# Domain profile dataclass
# ---------------------------------------------------------------------------

@dataclass
class DomainProfile:
    """
    Keyword lists for a single business domain, separated into four priority tiers.

    Design rule
    -----------
    - high:     industry-exclusive terms that rarely appear in other domains
    - medium:   domain-specific but shared with at most one or two adjacent domains
    - low:      generic context words that weakly signal the domain
    - negative: strong indicators of a *different* domain — penalise this domain
                if these appear (prevents generic words from cross-contaminating)
    """
    display_name:  str
    high:          list[str] = field(default_factory=list)
    medium:        list[str] = field(default_factory=list)
    low:           list[str] = field(default_factory=list)
    negative:      list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Keyword registry — 21 business domains
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, DomainProfile] = {

    # ── Sales ─────────────────────────────────────────────────────────────
    "sales": DomainProfile(
        display_name="Sales",
        high=[
            "revenue", "sales", "orders", "order", "pipeline",
            "quota", "commission", "won", "lost", "deal",
            "opportunity", "forecast", "bookings", "upsell", "cross_sell",
        ],
        medium=[
            "profit", "discount", "price", "amount", "invoice",
            "account", "territory", "rep", "quantity", "qty",
            "customer", "product", "closed", "contract",
        ],
        low=["date", "region", "status", "id", "name", "total"],
        negative=[
            "patient", "diagnosis", "student", "enrollment",
            "ticket", "sla", "churn", "sku", "warehouse",
            "claim", "policy", "reservation", "kwh",
        ],
    ),

    # ── Marketing ─────────────────────────────────────────────────────────
    "marketing": DomainProfile(
        display_name="Marketing",
        high=[
            "campaign", "impressions", "ctr", "roas", "roi",
            "clicks", "click", "conversion", "conversions", "leads",
            "lead", "attribution", "utm", "cpc", "cpm",
            "awareness", "funnel", "retargeting", "engagement",
        ],
        medium=[
            "spend", "budget", "channel", "medium", "source",
            "ad", "bounce", "session", "reach", "acquisition",
            "promotion", "creative", "audience", "email", "open_rate",
        ],
        low=["date", "customer", "revenue", "status", "id"],
        negative=[
            "patient", "diagnosis", "employee", "salary",
            "ticket", "sla", "sku", "warehouse", "reservation",
            "claim", "policy", "kwh", "mortgage",
        ],
    ),

    # ── Finance ───────────────────────────────────────────────────────────
    "finance": DomainProfile(
        display_name="Finance",
        high=[
            "expense", "expenses", "ebitda", "ledger", "debit", "credit",
            "reconciliation", "accrual", "amortisation", "depreciation",
            "cashflow", "cash_flow", "net_income", "gross_profit",
            "liability", "equity", "asset", "audit", "accounts_payable",
            "accounts_receivable", "journal",
        ],
        medium=[
            "revenue", "profit", "loss", "budget", "cost", "tax",
            "invoice", "balance", "forecast", "actuals", "margin",
            "income", "expenditure", "allocation", "variance",
        ],
        low=["date", "account", "department", "period", "total", "amount"],
        negative=[
            "patient", "diagnosis", "student", "enrollment",
            "churn", "roaming", "ticket", "sla", "warehouse",
            "sku", "reservation", "kwh", "campaign",
        ],
    ),

    # ── Human Resources ───────────────────────────────────────────────────
    "hr": DomainProfile(
        display_name="HR",
        high=[
            "employee", "payroll", "attrition", "workforce", "headcount",
            "hire", "hiring", "termination", "resignation", "appraisal",
            "onboarding", "offboarding", "leave", "absence", "diversity",
            "fte",
        ],
        medium=[
            "salary", "compensation", "bonus", "department", "tenure",
            "performance", "grade", "job", "position", "manager",
            "training", "engagement", "staff", "worker",
        ],
        low=["date", "name", "gender", "age", "id", "location"],
        negative=[
            "patient", "diagnosis", "student", "enrollment",
            "churn", "roaming", "ticket", "sla", "campaign",
            "sku", "warehouse", "reservation", "mortgage", "claim",
        ],
    ),

    # ── Operations ────────────────────────────────────────────────────────
    "operations": DomainProfile(
        display_name="Operations",
        high=[
            "throughput", "utilization", "oee", "downtime", "cycle_time",
            "takt", "scrap", "rework", "yield", "defect",
            "uptime", "availability", "mtbf", "mttr",
        ],
        medium=[
            "process", "efficiency", "maintenance", "schedule", "shift",
            "line", "plant", "capacity", "delivery", "output",
            "workorder", "machine", "equipment", "asset",
        ],
        low=["date", "status", "id", "quantity", "unit", "location"],
        negative=[
            "patient", "diagnosis", "student", "enrollment",
            "churn", "roaming", "campaign", "mortgage", "claim",
            "reservation", "kwh",
        ],
    ),

    # ── Inventory ─────────────────────────────────────────────────────────
    "inventory": DomainProfile(
        display_name="Inventory",
        high=[
            "warehouse", "sku", "reorder", "reorder_point", "on_hand",
            "inventory", "stock", "stockout", "shrinkage", "putaway",
            "picking", "receiving", "barcode", "bin", "shelf",
            "expiry", "batch", "lot", "depot",
        ],
        medium=[
            "supplier", "lead_time", "quantity", "fulfillment",
            "demand", "product", "unit", "location", "storage",
        ],
        low=["date", "id", "status", "category", "name"],
        negative=[
            "patient", "diagnosis", "student", "enrollment",
            "churn", "roaming", "campaign", "mortgage", "claim",
            "reservation", "salary", "employee",
        ],
    ),

    # ── Customer Support ──────────────────────────────────────────────────
    "customer_support": DomainProfile(
        display_name="Customer Support",
        high=[
            "ticket", "sla", "escalation", "csat", "nps",
            "first_contact", "reopen", "queue", "handle_time",
            "resolution_time", "response_time",
        ],
        medium=[
            "case", "resolution", "satisfaction", "agent", "complaint",
            "support", "issue", "sentiment", "priority", "channel",
        ],
        low=["date", "customer", "status", "id", "category"],
        negative=[
            "patient", "diagnosis", "student", "enrollment",
            "churn", "roaming", "campaign", "mortgage", "sku",
            "warehouse", "reservation", "salary",
        ],
    ),

    # ── Healthcare ────────────────────────────────────────────────────────
    "healthcare": DomainProfile(
        display_name="Healthcare",
        high=[
            "patient", "diagnosis", "icd", "icd10", "readmission",
            "prescription", "medication", "procedure", "vital",
            "lab", "discharge", "los", "length_of_stay", "clinical",
            "hospital", "nurse", "doctor", "physician",
        ],
        medium=[
            "treatment", "admission", "condition", "insurance",
            "clinic", "member", "symptom", "ehr", "emr",
            "appointment", "encounter", "referral",
        ],
        low=["date", "age", "gender", "id", "status"],
        negative=[
            "employee", "salary", "campaign", "ctr", "sku",
            "warehouse", "reservation", "mortgage", "churn", "roaming",
        ],
    ),

    # ── Education ─────────────────────────────────────────────────────────
    "education": DomainProfile(
        display_name="Education",
        high=[
            "student", "enrollment", "gpa", "curriculum", "degree",
            "faculty", "institution", "cohort", "credit", "pass", "fail",
            "semester", "term", "lecture", "assignment",
        ],
        medium=[
            "grade", "course", "attendance", "exam", "teacher",
            "subject", "class", "score", "quiz", "transcript",
        ],
        low=["date", "id", "status", "name", "age", "gender"],
        negative=[
            "patient", "diagnosis", "employee", "salary",
            "campaign", "ctr", "sku", "warehouse", "mortgage",
            "claim", "churn", "reservation",
        ],
    ),

    # ── Telecommunications ────────────────────────────────────────────────
    "telecommunications": DomainProfile(
        display_name="Telecommunications",
        high=[
            "churn", "arpu", "msisdn", "roaming", "broadband",
            "prepaid", "postpaid", "lte", "sim", "carrier",
            "data_usage", "minutes", "calls", "network", "coverage",
            "voip", "fiber", "wireless", "mobile", "telecom",
        ],
        medium=[
            "phone", "internet", "service", "charges", "contract",
            "tenure", "plan", "subscription", "billing", "bundle",
            "provider", "cable", "monthly",
        ],
        low=["date", "customer", "id", "gender", "age", "status", "total"],
        negative=[
            "patient", "diagnosis", "employee", "salary",
            "student", "enrollment", "campaign", "sku",
            "warehouse", "mortgage", "claim", "reservation",
        ],
    ),

    # ── Banking ───────────────────────────────────────────────────────────
    "banking": DomainProfile(
        display_name="Banking",
        high=[
            "transaction", "loan", "mortgage", "interest_rate",
            "credit_score", "fico", "branch", "deposit", "withdrawal",
            "overdraft", "collateral", "default", "repayment",
            "installment", "disbursement",
        ],
        medium=[
            "account", "balance", "credit", "debit", "savings",
            "checking", "transfer", "wire", "beneficiary",
            "customer", "product",
        ],
        low=["date", "id", "status", "amount", "currency"],
        negative=[
            "patient", "diagnosis", "student", "enrollment",
            "churn", "roaming", "campaign", "sku", "warehouse",
            "reservation", "employee", "salary",
        ],
    ),

    # ── Insurance ─────────────────────────────────────────────────────────
    "insurance": DomainProfile(
        display_name="Insurance",
        high=[
            "claim", "policy", "premium", "underwriting", "actuary",
            "deductible", "insured", "policyholder", "coverage",
            "beneficiary", "risk", "liability", "reinsurance",
            "adjuster", "loss_ratio",
        ],
        medium=[
            "renewal", "endorsement", "exclusion", "indemnity",
            "accident", "incident", "exposure",
        ],
        low=["date", "customer", "id", "status", "amount", "type"],
        negative=[
            "patient", "diagnosis", "student", "enrollment",
            "churn", "roaming", "campaign", "sku", "warehouse",
            "reservation", "salary",
        ],
    ),

    # ── Retail ────────────────────────────────────────────────────────────
    "retail": DomainProfile(
        display_name="Retail",
        high=[
            "pos", "store", "checkout", "receipt", "footfall",
            "basket", "category", "planogram", "markdown", "shelf",
        ],
        medium=[
            "sku", "product", "price", "discount", "promotion",
            "customer", "quantity", "sales", "inventory",
        ],
        low=["date", "id", "status", "region", "name"],
        negative=[
            "patient", "diagnosis", "student", "enrollment",
            "churn", "roaming", "campaign", "mortgage", "claim",
            "reservation", "salary", "employee",
        ],
    ),

    # ── E-commerce ────────────────────────────────────────────────────────
    "ecommerce": DomainProfile(
        display_name="E-commerce",
        high=[
            "cart", "wishlist", "product_view", "add_to_cart",
            "checkout", "session", "pageview", "funnel",
            "abandonment", "return", "refund", "review", "rating",
        ],
        medium=[
            "order", "shipping", "payment", "coupon", "discount",
            "customer", "product", "sku", "click",
        ],
        low=["date", "id", "status", "amount", "category"],
        negative=[
            "patient", "diagnosis", "employee", "salary",
            "churn", "roaming", "mortgage", "claim", "reservation",
            "kwh",
        ],
    ),

    # ── Manufacturing ─────────────────────────────────────────────────────
    "manufacturing": DomainProfile(
        display_name="Manufacturing",
        high=[
            "bom", "work_order", "production_run", "tooling", "mold",
            "assembly", "fabrication", "welding", "machining",
            "routing", "work_center",
        ],
        medium=[
            "batch", "defect", "yield", "quality", "machine",
            "shift", "line", "plant", "quantity", "output",
        ],
        low=["date", "id", "status", "unit", "cost"],
        negative=[
            "patient", "diagnosis", "student", "campaign",
            "churn", "roaming", "mortgage", "claim", "reservation",
            "salary",
        ],
    ),

    # ── Supply Chain ──────────────────────────────────────────────────────
    "supply_chain": DomainProfile(
        display_name="Supply Chain",
        high=[
            "shipment", "freight", "carrier", "customs", "incoterms",
            "purchase_order", "po", "grn", "asn", "3pl", "fob",
            "dap", "dock",
        ],
        medium=[
            "supplier", "lead_time", "delivery", "warehouse", "logistics",
            "distribution", "route", "transportation", "vendor",
        ],
        low=["date", "id", "status", "quantity", "location"],
        negative=[
            "patient", "diagnosis", "student", "campaign", "churn",
            "mortgage", "claim", "reservation", "salary",
        ],
    ),

    # ── Hospitality ───────────────────────────────────────────────────────
    "hospitality": DomainProfile(
        display_name="Hospitality",
        high=[
            "reservation", "checkin", "checkout", "occupancy", "adr",
            "revpar", "folio", "housekeeping", "amenity", "front_desk",
            "concierge", "banquet", "room_type",
        ],
        medium=[
            "guest", "room", "rate", "stay", "hotel", "nights",
            "booking", "channel",
        ],
        low=["date", "id", "status", "amount", "name"],
        negative=[
            "patient", "diagnosis", "employee", "salary", "campaign",
            "churn", "sku", "warehouse", "mortgage", "claim",
        ],
    ),

    # ── Real Estate ───────────────────────────────────────────────────────
    "real_estate": DomainProfile(
        display_name="Real Estate",
        high=[
            "property", "listing", "lease", "tenant", "sqft",
            "bedrooms", "bathrooms", "zoning", "appraisal", "deed",
            "mls", "foreclosure", "hoa", "vacancy",
        ],
        medium=[
            "mortgage", "rent", "sale_price", "agent", "broker",
            "location", "address", "floor", "unit",
        ],
        low=["date", "id", "status", "amount", "type"],
        negative=[
            "patient", "diagnosis", "student", "campaign", "churn",
            "roaming", "sku", "warehouse", "salary",
        ],
    ),

    # ── Energy ────────────────────────────────────────────────────────────
    "energy": DomainProfile(
        display_name="Energy",
        high=[
            "kwh", "mwh", "consumption", "meter", "tariff", "grid",
            "generation", "solar", "wind", "peak", "offpeak",
            "demand_response", "carbon", "emissions", "renewable",
        ],
        medium=[
            "usage", "billing_period", "rate", "utility",
            "customer", "supply", "distribution",
        ],
        low=["date", "id", "status", "amount", "location"],
        negative=[
            "patient", "diagnosis", "student", "campaign", "churn",
            "sku", "warehouse", "mortgage", "claim", "reservation",
        ],
    ),

    # ── Government ────────────────────────────────────────────────────────
    "government": DomainProfile(
        display_name="Government",
        high=[
            "constituent", "permit", "ordinance", "municipality",
            "precinct", "ward", "bureau", "regulation", "statute",
            "license", "compliance", "violation", "fines", "levy",
        ],
        medium=[
            "application", "department", "approval", "inspection",
            "agency", "public",
        ],
        low=["date", "id", "status", "amount", "name", "address"],
        negative=[
            "patient", "campaign", "churn", "sku", "warehouse",
            "mortgage", "reservation",
        ],
    ),

    # ── SaaS / Product Analytics ──────────────────────────────────────────
    "saas": DomainProfile(
        display_name="SaaS / Product Analytics",
        high=[
            "mrr", "arr", "dau", "mau", "wau", "ltv", "cac",
            "churn", "expansion", "contraction", "nrr",
            "activation", "retention", "cohort", "feature_adoption",
            "session_duration", "onboarding",
        ],
        medium=[
            "subscription", "user", "feature", "plan", "trial",
            "event", "pageview", "session", "conversion",
            "upgrade", "downgrade", "tier",
        ],
        low=["date", "id", "status", "amount", "account"],
        negative=[
            "patient", "diagnosis", "employee", "salary",
            "sku", "warehouse", "mortgage", "claim",
            "reservation", "kwh",
        ],
    ),
}


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

def _tokenise(name: str) -> set[str]:
    """
    Decompose a column name into a set of normalised lowercase tokens.

    Handles the following naming styles correctly:
        camelCase      → "orderDate"       → {"order", "date"}
        PascalCase     → "CustomerID"      → {"customer", "id"}
        acronym_word   → "TLSConfig"       → {"tls", "config"}
        snake_case     → "avg_order_value" → {"avg", "order", "value"}
        space-sep      → "Monthly Charges" → {"monthly", "charges"}
        hyphenated     → "first-name"      → {"first", "name"}
        ALL_CAPS       → "TOTAL_REVENUE"   → {"total", "revenue"}

    Tokens shorter than 2 characters are discarded (removes noise from
    abbreviated suffixes like "s" or single-letter abbreviations).
    """
    # Step 1: split lowercase-then-uppercase boundary ("orderDate" → "order Date")
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)

    # Step 2: split consecutive-uppercase-then-word boundary ("TLSConfig" → "TLS Config")
    s = re.sub(r"([A-Z]{2,})([A-Z][a-z])", r"\1 \2", s)

    # Step 3: split on all common delimiters, then lowercase
    parts = re.split(r"[\s_\-./|,;:()]+", s.lower())

    # Step 4: filter — keep only tokens ≥ 2 characters that are alphanumeric
    return {t for t in parts if len(t) >= 2 and t.isalnum()}


# ---------------------------------------------------------------------------
# Per-domain scoring
# ---------------------------------------------------------------------------

def _score_domain(
    all_tokens: set[str],
    token_to_cols: dict[str, list[str]],
    profile: DomainProfile,
) -> dict:
    """
    Score a single domain against the full token set extracted from column names.

    Returns a breakdown dict:
        raw_score       — sum of points from all tiers (may be negative)
        high_pts        — points from high-priority matches only
        medium_pts      — points from medium-priority matches only
        matched_tokens  — deduplicated list of matched keyword tokens
        matched_columns — deduplicated list of original column names that matched
    """
    # Build lookup sets for each tier (use sets for O(1) lookup)
    high_set     = set(profile.high)
    medium_set   = set(profile.medium)
    low_set      = set(profile.low)
    negative_set = set(profile.negative)

    raw_score     = 0
    high_pts      = 0
    medium_pts    = 0
    matched_tokens:  list[str] = []
    matched_col_set: set[str]  = set()

    for token in all_tokens:
        # Determine which tier this token hits — process from highest to lowest
        # so a token in multiple tiers only counts once (at the highest tier).
        if token in high_set:
            raw_score += HIGH_WEIGHT
            high_pts  += HIGH_WEIGHT
            matched_tokens.append(token)
            matched_col_set.update(token_to_cols.get(token, []))
        elif token in medium_set:
            raw_score  += MEDIUM_WEIGHT
            medium_pts += MEDIUM_WEIGHT
            matched_tokens.append(token)
            matched_col_set.update(token_to_cols.get(token, []))
        elif token in low_set:
            raw_score += LOW_WEIGHT
            matched_tokens.append(token)
            matched_col_set.update(token_to_cols.get(token, []))

        # Negative check — independent, can stack with any positive tier
        if token in negative_set:
            raw_score += NEGATIVE_WEIGHT

    return {
        "raw_score":       raw_score,
        "high_pts":        high_pts,
        "medium_pts":      medium_pts,
        "matched_tokens":  matched_tokens,
        "matched_columns": list(matched_col_set),
    }


# ---------------------------------------------------------------------------
# Confidence calculation
# ---------------------------------------------------------------------------

def _compute_confidence(
    score_breakdown: dict,
    n_columns: int,
) -> float:
    """
    Convert a domain's raw score breakdown into a composite confidence value
    in [0, 1].

    Three sub-scores are blended:

    weighted_score_norm
        Raw domain score divided by the theoretical maximum score
        (every column matches a high-priority keyword).  This rewards
        datasets that have many domain-specific matches.

    coverage_score
        Fraction of dataset columns that matched any keyword.
        Penalises domains where only one or two stray generic words matched.

    specificity_score
        Fraction of positive points coming from high + medium tiers.
        Penalises domains where the score is entirely composed of +1 generic
        words — those matches are coincidental.

    The three sub-scores are blended with weights defined at the top of this
    module (W_SCORE, W_COVERAGE, W_SPECIFICITY).
    """
    raw_score      = score_breakdown["raw_score"]
    high_pts       = score_breakdown["high_pts"]
    medium_pts     = score_breakdown["medium_pts"]
    matched_tokens = score_breakdown["matched_tokens"]
    matched_cols   = score_breakdown["matched_columns"]

    if raw_score <= 0 or not matched_tokens:
        return 0.0

    # Maximum achievable score: every column matches a high-priority keyword
    max_score = n_columns * HIGH_WEIGHT

    # 1. Weighted score — normalised by maximum achievable
    weighted_score_norm = min(1.0, raw_score / max_score)

    # 2. Coverage — fraction of columns that contributed any match
    coverage_score = len(matched_cols) / n_columns

    # 3. Specificity — fraction of positive score from high + medium tiers
    positive_score   = sum(
        HIGH_WEIGHT if raw_score > 0 else 0
        for _ in [None]  # placeholder; calculate below
    )
    positive_score   = max(raw_score, 1)  # raw_score already excludes negatives sum
    quality_pts      = high_pts + medium_pts
    # Re-compute positive_score as raw score before negatives
    # (we want the *positive* tier contribution, not the penalised total)
    specificity_score = quality_pts / max(quality_pts + (raw_score - quality_pts + abs(raw_score - quality_pts)) / 2, 1)
    # Simpler formulation: quality ratio = high+medium points / all positive points scored
    # All positive points = sum of all tier hits (ignoring negatives)
    total_positive = quality_pts + (raw_score - quality_pts - (raw_score - quality_pts if raw_score >= quality_pts else 0))
    # Clean up: just use high+med / (high+med+low)
    low_pts = raw_score - quality_pts - score_breakdown.get("negative_total", 0)
    if quality_pts + max(low_pts, 0) > 0:
        specificity_score = quality_pts / (quality_pts + max(low_pts, 0))
    else:
        specificity_score = 0.0

    # Blend
    composite = (
        W_SCORE       * weighted_score_norm
        + W_COVERAGE    * coverage_score
        + W_SPECIFICITY * specificity_score
    )

    return min(1.0, composite)


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------

class BusinessClassifier:
    """
    Production-quality business domain classifier for InsightPilot AI.

    Uses a tiered keyword registry with weighted scoring to determine which
    business domain best matches the column names of an uploaded dataset.
    Falls back to ``"generic"`` if no domain meets the confidence threshold.
    """

    def classify(self, column_names: list[str]) -> dict:
        """
        Detect the business domain from a list of column names.

        Parameters
        ----------
        column_names : list[str]
            Raw column names from the uploaded DataFrame.

        Returns
        -------
        dict with keys:
            domain           — snake_case domain id (e.g. "telecommunications")
            confidence       — integer 0–100
            matched_columns  — column names that contributed to the winning domain
            matched_keywords — specific keywords that were matched
            top_candidates   — list of top-N {"domain": display_name, "score": int}
        """
        if not column_names:
            return self._empty_result()

        n_columns = len(column_names)

        # ── Step 1: Tokenise all column names ──────────────────────────────
        # token_to_cols maps each token to the original column name(s) that
        # produced it, so we can surface matched columns in the result.
        token_to_cols: dict[str, list[str]] = {}
        for col in column_names:
            for tok in _tokenise(col):
                token_to_cols.setdefault(tok, []).append(col)

        all_tokens: set[str] = set(token_to_cols)

        # ── Step 2: Score every domain ─────────────────────────────────────
        domain_scores: list[tuple[str, float, dict]] = []

        for domain_id, profile in _REGISTRY.items():
            breakdown = _score_domain(all_tokens, token_to_cols, profile)
            confidence = _compute_confidence(breakdown, n_columns)
            domain_scores.append((domain_id, confidence, breakdown))

        # ── Step 3: Rank by confidence ─────────────────────────────────────
        domain_scores.sort(key=lambda x: x[1], reverse=True)

        # ── Step 4: Pick winner or fall back to generic ────────────────────
        best_id, best_conf, best_breakdown = domain_scores[0]

        if best_conf < MIN_CONFIDENCE_THRESHOLD:
            return {
                "domain":          "generic",
                "confidence":      min(95, round(best_conf * 100)),
                "matched_columns": [],
                "matched_keywords": [],
                "top_candidates": self._top_candidates(domain_scores),
            }

        # Cap confidence at 95 — keyword matching is inherently imprecise
        confidence_pct = min(95, round(best_conf * 100))

        return {
            "domain":           best_id,
            "confidence":       confidence_pct,
            "matched_columns":  best_breakdown["matched_columns"],
            "matched_keywords": best_breakdown["matched_tokens"],
            "top_candidates":   self._top_candidates(domain_scores),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _top_candidates(
        ranked: list[tuple[str, float, dict]],
    ) -> list[dict]:
        """Return the top-N candidates as display-name + integer score dicts."""
        result = []
        for domain_id, conf, _ in ranked[:TOP_N_CANDIDATES]:
            profile = _REGISTRY.get(domain_id)
            display = profile.display_name if profile else domain_id.replace("_", " ").title()
            result.append({
                "domain": display,
                "score":  min(95, round(conf * 100)),
            })
        return result

    @staticmethod
    def _empty_result() -> dict:
        return {
            "domain":           "generic",
            "confidence":       0,
            "matched_columns":  [],
            "matched_keywords": [],
            "top_candidates":   [],
        }
