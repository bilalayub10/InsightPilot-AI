"""
InsightPilot AI — Report Generator Service.

Orchestration-only layer: consumes cached analysis results already produced
by AnalyticsService, BusinessClassifier, KPIDetector, ChartPlanner,
ChartInsights, CEOBriefing, AnomalyDetector, and BusinessContextBuilder.

No analytics are re-run here.  The only new work is:
  1. Rendering chart images from pre-computed data points via matplotlib.
  2. Composing the PDF layout via ReportLab.
"""

from __future__ import annotations

import io
import math
import textwrap
from datetime import datetime, timezone
from typing import Any

import matplotlib
matplotlib.use("Agg")          # non-interactive backend — no display needed
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, NextPageTemplate,
    Paragraph, Spacer, Table, TableStyle, Image, HRFlowable,
    KeepTogether, PageBreak,
)
from reportlab.platypus.flowables import Flowable

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

NAVY      = colors.HexColor("#1E3A5F")
BLUE      = colors.HexColor("#2563EB")
BLUE_LIGHT= colors.HexColor("#DBEAFE")
SLATE     = colors.HexColor("#64748B")
SLATE_LIGHT = colors.HexColor("#F1F5F9")
WHITE     = colors.white
AMBER     = colors.HexColor("#D97706")
RED       = colors.HexColor("#DC2626")
GREEN     = colors.HexColor("#16A34A")
CHARCOAL  = colors.HexColor("#1E293B")

CHART_PALETTE = [
    "#3B82F6", "#06B6D4", "#8B5CF6", "#22C55E",
    "#F59E0B", "#EF4444", "#14B8A6", "#EC4899",
]

W, H = A4  # 595.28 × 841.89 pt
MARGIN = 20 * mm


# ---------------------------------------------------------------------------
# Utility flowables
# ---------------------------------------------------------------------------

class ColorBar(Flowable):
    """A full-width horizontal colour bar (used as section header background)."""
    def __init__(self, text: str, bg=NAVY, fg=WHITE, height=22, font_size=11):
        super().__init__()
        self.text = text
        self.bg = bg
        self.fg = fg
        self._height = height
        self.font_size = font_size
        self.width = W - 2 * MARGIN

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.roundRect(0, 0, self.width, self._height, 4, fill=1, stroke=0)
        c.setFillColor(self.fg)
        c.setFont("Helvetica-Bold", self.font_size)
        c.drawString(10, 6, self.text)

    def wrap(self, *_):
        return self.width, self._height


class InfoCard(Flowable):
    """Two-column KV card row used in Dataset Overview."""
    def __init__(self, pairs: list[tuple[str, str]], col_width=None):
        super().__init__()
        self.pairs = pairs
        self._col_width = col_width or (W - 2 * MARGIN) / 2
        self.width = W - 2 * MARGIN

    def draw(self):
        c = self.canv
        row_h = 22
        for i, (k, v) in enumerate(self.pairs):
            x = (i % 2) * self._col_width
            y = -((i // 2) * row_h)
            # background
            fill = SLATE_LIGHT if (i // 2) % 2 == 0 else WHITE
            c.setFillColor(fill)
            c.rect(x, y - row_h + 4, self._col_width - 2, row_h - 2, fill=1, stroke=0)
            c.setFillColor(SLATE)
            c.setFont("Helvetica", 8)
            c.drawString(x + 6, y - row_h + 10, k)
            c.setFillColor(CHARCOAL)
            c.setFont("Helvetica-Bold", 9)
            c.drawRightString(x + self._col_width - 8, y - row_h + 10, str(v))

    def wrap(self, *_):
        rows = math.ceil(len(self.pairs) / 2)
        return self.width, rows * 22


# ---------------------------------------------------------------------------
# Style registry
# ---------------------------------------------------------------------------

def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    s: dict[str, ParagraphStyle] = {}

    def add(name, **kw):
        s[name] = ParagraphStyle(name, **kw)

    add("cover_title",
        fontName="Helvetica-Bold", fontSize=28, textColor=WHITE,
        alignment=TA_CENTER, spaceAfter=6, leading=34)
    add("cover_sub",
        fontName="Helvetica", fontSize=14, textColor=colors.HexColor("#CBD5E1"),
        alignment=TA_CENTER, spaceAfter=4, leading=18)
    add("cover_meta",
        fontName="Helvetica", fontSize=11, textColor=colors.HexColor("#94A3B8"),
        alignment=TA_CENTER, leading=15)

    add("section_intro",
        fontName="Helvetica", fontSize=10, textColor=SLATE,
        alignment=TA_LEFT, spaceAfter=8, leading=14)
    add("body",
        fontName="Helvetica", fontSize=10, textColor=CHARCOAL,
        alignment=TA_JUSTIFY, spaceAfter=6, leading=15)
    add("body_small",
        fontName="Helvetica", fontSize=9, textColor=SLATE,
        alignment=TA_LEFT, spaceAfter=4, leading=13)
    add("bold",
        fontName="Helvetica-Bold", fontSize=10, textColor=CHARCOAL,
        alignment=TA_LEFT, spaceAfter=4, leading=14)
    add("kv_label",
        fontName="Helvetica", fontSize=8, textColor=SLATE, leading=11)
    add("kv_value",
        fontName="Helvetica-Bold", fontSize=9, textColor=CHARCOAL, leading=12)
    add("chart_title",
        fontName="Helvetica-Bold", fontSize=10, textColor=NAVY,
        spaceAfter=3, leading=14)
    add("chart_question",
        fontName="Helvetica-Oblique", fontSize=8, textColor=SLATE,
        spaceAfter=6, leading=11)
    add("insight_label",
        fontName="Helvetica-Bold", fontSize=9, textColor=BLUE,
        spaceAfter=2, leading=12)
    add("insight_body",
        fontName="Helvetica", fontSize=9, textColor=CHARCOAL,
        alignment=TA_JUSTIFY, spaceAfter=4, leading=13)
    add("bullet",
        fontName="Helvetica", fontSize=9, textColor=CHARCOAL,
        leftIndent=12, spaceAfter=4, leading=13,
        bulletIndent=0, bulletFontName="Helvetica-Bold", bulletFontSize=9)
    add("risk_high",
        fontName="Helvetica-Bold", fontSize=9, textColor=RED, leading=12)
    add("risk_medium",
        fontName="Helvetica-Bold", fontSize=9, textColor=AMBER, leading=12)
    add("risk_low",
        fontName="Helvetica-Bold", fontSize=9, textColor=GREEN, leading=12)
    add("action_priority",
        fontName="Helvetica-Bold", fontSize=8, textColor=BLUE, leading=11)
    add("footer_text",
        fontName="Helvetica", fontSize=7, textColor=SLATE, leading=9)
    return s


# ---------------------------------------------------------------------------
# Chart rendering (matplotlib → PNG → BytesIO)
# ---------------------------------------------------------------------------

def _render_chart(chart: dict, width_pt: float = 240, height_pt: float = 150) -> io.BytesIO | None:
    data = chart.get("data", [])
    if not data:
        return None

    labels = [str(d.get("label", ""))[:18] for d in data]
    values = [float(d.get("value", 0)) for d in data]
    chart_type = chart.get("type", "bar")
    title = chart.get("title", "")
    palette = CHART_PALETTE

    dpi = 144
    fig_w = width_pt / 72
    fig_h = height_pt / 72

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#F8FAFC")
    for spine in ax.spines.values():
        spine.set_visible(False)

    try:
        if chart_type in ("bar", "histogram"):
            cols = [palette[i % len(palette)] for i in range(len(labels))]
            bars = ax.bar(range(len(labels)), values, color=cols, width=0.6, zorder=3)
            ax.set_xticks(range(len(labels)))
            if len(labels) > 6 or max((len(l) for l in labels), default=0) > 8:
                ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=7)
            else:
                ax.set_xticklabels(labels, fontsize=7)
            ax.tick_params(axis="y", labelsize=7)
            ax.yaxis.grid(True, color="#E2E8F0", zorder=0)
            ax.tick_params(bottom=False, left=False)

        elif chart_type == "line":
            ax.plot(range(len(labels)), values, color=palette[0],
                    linewidth=2, marker="o", markersize=3, zorder=3)
            ax.fill_between(range(len(labels)), values,
                            alpha=0.08, color=palette[0])
            if len(labels) > 8:
                step = max(1, len(labels) // 6)
                ticks = list(range(0, len(labels), step))
                ax.set_xticks(ticks)
                ax.set_xticklabels([labels[i] for i in ticks], rotation=35, ha="right", fontsize=7)
            else:
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels, fontsize=7)
            ax.tick_params(axis="y", labelsize=7)
            ax.yaxis.grid(True, color="#E2E8F0", zorder=0)
            ax.tick_params(bottom=False, left=False)

        elif chart_type == "pie":
            wedge_colors = [palette[i % len(palette)] for i in range(len(labels))]
            wedges, texts, autotexts = ax.pie(
                values, labels=None, colors=wedge_colors,
                autopct=lambda p: f"{p:.0f}%" if p >= 4 else "",
                pctdistance=0.72, startangle=90,
                wedgeprops={"linewidth": 1, "edgecolor": "white"},
            )
            for t in autotexts:
                t.set_fontsize(7)
                t.set_color("white")
                t.set_fontweight("bold")
            # Legend outside
            ax.legend(
                wedges, [l[:16] for l in labels],
                loc="center left", bbox_to_anchor=(1, 0.5),
                fontsize=6.5, frameon=False,
            )
            ax.axis("equal")

        elif chart_type == "scatter":
            x_vals = [float(d.get("label", 0)) if _is_numeric(d.get("label", "")) else i
                      for i, d in enumerate(data)]
            ax.scatter(x_vals, values, color=palette[0], alpha=0.55, s=18, zorder=3)
            ax.yaxis.grid(True, color="#E2E8F0", zorder=0)
            ax.tick_params(labelsize=7, bottom=False, left=False)

        else:
            return None

        if chart_type != "pie":
            ax.set_title(title, fontsize=8, fontweight="bold", color="#1E3A5F", pad=5)

        fig.tight_layout(pad=0.6)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        buf.seek(0)
        return buf

    except Exception:
        return None
    finally:
        plt.close(fig)


def _is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Page templates (cover vs content)
# ---------------------------------------------------------------------------

def _add_page_number(canvas, doc):
    """Footer on every content page."""
    canvas.saveState()
    canvas.setFillColor(SLATE)
    canvas.setFont("Helvetica", 7)
    page_num = doc.page
    canvas.drawRightString(W - MARGIN, 10 * mm, f"Page {page_num}")
    canvas.drawString(MARGIN, 10 * mm, "InsightPilot AI — Executive Business Analysis Report")
    canvas.restoreState()


def _cover_page(canvas, doc):
    """Full-bleed navy cover page background."""
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # Blue accent strip at top
    canvas.setFillColor(BLUE)
    canvas.rect(0, H - 18 * mm, W, 8 * mm, fill=1, stroke=0)
    # Subtle diagonal watermark lines
    canvas.setStrokeColor(colors.HexColor("#243B55"))
    canvas.setLineWidth(0.5)
    for i in range(0, int(W) + int(H), 40):
        canvas.line(i, 0, 0, i)
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report(analysis: dict) -> bytes:
    """
    Build a professional executive PDF from cached analysis data.

    Parameters
    ----------
    analysis : dict
        The full AnalyzeResult payload (as returned by /api/analyze).

    Returns
    -------
    bytes
        Raw PDF bytes ready to stream to the client.
    """
    buf = io.BytesIO()
    styles = _build_styles()

    # -- Document setup ----------------------------------------------------
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=18 * mm,
        title="InsightPilot Executive Report",
        author="InsightPilot AI",
    )

    content_frame = Frame(
        MARGIN, 18 * mm,
        W - 2 * MARGIN, H - MARGIN - 18 * mm,
        id="content",
    )
    cover_frame = Frame(
        MARGIN, MARGIN,
        W - 2 * MARGIN, H - 2 * MARGIN,
        id="cover",
    )

    doc.addPageTemplates([
        PageTemplate(id="cover_tpl", frames=[cover_frame], onPage=_cover_page),
        PageTemplate(id="content_tpl", frames=[content_frame], onPage=_add_page_number),
    ])

    story: list = []

    # =========================================================================
    # COVER PAGE
    # =========================================================================
    story.append(NextPageTemplate("cover_tpl"))

    ceo = analysis.get("ceoBriefing") or {}
    bctx = analysis.get("businessContext") or {}
    kpis = analysis.get("kpis", [])
    charts = analysis.get("charts", [])
    insights = analysis.get("insights", [])
    analyzed_at = analysis.get("analyzedAt", datetime.now(timezone.utc).isoformat())
    dataset_id = analysis.get("datasetId", "—")

    domain = ceo.get("business_domain") or "General Business"
    confidence = ceo.get("confidence", 0)

    try:
        ts = datetime.fromisoformat(analyzed_at.replace("Z", "+00:00"))
        ts_str = ts.strftime("%B %d, %Y  %H:%M UTC")
    except Exception:
        ts_str = analyzed_at

    # Vertical centering: push content down ~30% from top
    story.append(Spacer(1, 80 * mm))

    story.append(Paragraph("InsightPilot AI", styles["cover_title"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Executive Business Analysis Report", styles["cover_sub"]))
    story.append(Spacer(1, 14 * mm))

    # Divider
    story.append(HRFlowable(width="60%", thickness=1, color=BLUE,
                             hAlign="CENTER", spaceAfter=12))

    story.append(Paragraph(f"Dataset: {dataset_id}", styles["cover_meta"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f"Business Domain: {domain}", styles["cover_meta"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f"Generated: {ts_str}", styles["cover_meta"]))

    # =========================================================================
    # CONTENT PAGES
    # =========================================================================
    story.append(NextPageTemplate("content_tpl"))
    story.append(PageBreak())

    # ------------------------------------------------------------------
    # 1. EXECUTIVE SUMMARY
    # ------------------------------------------------------------------
    story += _section("EXECUTIVE SUMMARY")
    summary = analysis.get("summary", "")
    # Break into sentences → artificial paragraphs for readability
    sentences = [s.strip() for s in summary.replace(". ", ".|").split("|") if s.strip()]
    para_text = " ".join(sentences)
    story.append(Paragraph(para_text, styles["body"]))

    # CEO briefing executive summary (AI narrative)
    ceo_summary = ceo.get("executive_summary", "")
    if ceo_summary:
        story.append(Spacer(1, 4 * mm))
        for para in _split_paragraphs(ceo_summary):
            story.append(Paragraph(para, styles["body"]))

    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------
    # 2. CEO BRIEFING CARDS
    # ------------------------------------------------------------------
    story += _section("CEO BRIEFING")

    health = ceo.get("overall_health") or {}
    health_score = health.get("score", "—")
    health_status = health.get("status", "—")

    briefing_rows = [
        ("Business Domain",    domain),
        ("Domain Confidence",  f"{confidence}%"),
        ("Overall Health",     f"{health_score}/100 — {health_status}"),
        ("Urgency",            ceo.get("urgency", "—")),
        ("Top Opportunity",    ceo.get("top_opportunity", "—")),
        ("Biggest Risk",       ceo.get("biggest_risk", "—")),
        ("Priority Action",    ceo.get("priority_action", "—")),
    ]
    story.append(_kv_table(briefing_rows))
    story.append(Spacer(1, 3 * mm))

    takeaways = ceo.get("key_takeaways", [])
    if takeaways:
        story.append(Paragraph("<b>Key Takeaways</b>", styles["bold"]))
        for t in takeaways:
            story.append(Paragraph(f"• {t}", styles["bullet"]))

    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------
    # 3. DATASET OVERVIEW
    # ------------------------------------------------------------------
    story += _section("DATASET OVERVIEW")

    quality_score = bctx.get("dataset_quality_score", "—")
    analysis_conf = bctx.get("analysis_confidence", "—")
    # Parse profile stats from summary string
    story.append(Paragraph(analysis.get("summary", ""), styles["body_small"]))
    story.append(Spacer(1, 3 * mm))

    overview_rows = [
        ("Business Domain",         domain),
        ("Classification Confidence", f"{confidence}%"),
        ("Analysis Confidence",      f"{analysis_conf}%" if analysis_conf != "—" else "—"),
        ("Dataset Quality Score",    f"{quality_score}/100" if quality_score != "—" else "—"),
    ]
    story.append(_kv_table(overview_rows))
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------
    # 4. TOP KPIs
    # ------------------------------------------------------------------
    if kpis:
        story += _section("KEY PERFORMANCE INDICATORS")
        kpi_data = [["KPI", "Value", "Trend"]]
        for k in kpis:
            trend_sym = {"up": "▲", "down": "▼", "flat": "→"}.get(k.get("trend", "flat"), "→")
            kpi_data.append([k.get("label", ""), k.get("value", ""), trend_sym])

        content_w_kpi = W - 2 * MARGIN
        tbl = Table(kpi_data, colWidths=[content_w_kpi - 140, 100, 40],
                    hAlign="LEFT", repeatRows=1)
        tbl.setStyle(TableStyle([
            # Header
            ("BACKGROUND",   (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING",(0, 0), (-1, 0), 7),
            ("TOPPADDING",   (0, 0), (-1, 0), 7),
            # Rows
            ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",     (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [SLATE_LIGHT, WHITE]),
            ("TOPPADDING",   (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 1), (-1, -1), 5),
            ("ALIGN",        (1, 0), (1, -1), "RIGHT"),
            ("ALIGN",        (2, 0), (2, -1), "CENTER"),
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
            ("LEFTPADDING",  (0, 0), (0, -1), 10),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------
    # 5. CHARTS
    # ------------------------------------------------------------------
    if charts:
        story += _section("DATA VISUALISATIONS")
        story.append(Paragraph(
            "Charts are derived from the exact same data shown in your executive dashboard.",
            styles["section_intro"]
        ))

        content_w = W - 2 * MARGIN          # 555 pt on A4
        chart_img_w = content_w             # full content width
        chart_img_h = round(chart_img_w * 0.44)   # ~16:7 aspect

        for chart in charts:
            chart_title = chart.get("title", "Chart")
            question    = chart.get("business_question", "")
            insight     = chart.get("insight") or {}

            # Keep title + image together so they don't split across pages
            img_buf = _render_chart(chart, width_pt=chart_img_w, height_pt=chart_img_h)
            header_elems = [Paragraph(chart_title, styles["chart_title"])]
            if question:
                header_elems.append(Paragraph(question, styles["chart_question"]))
            if img_buf:
                header_elems.append(Image(img_buf, width=chart_img_w, height=chart_img_h))
            else:
                header_elems.append(Paragraph("[Chart data unavailable]", styles["body_small"]))

            story.append(KeepTogether(header_elems))

            # AI insight panel — separate so it can flow naturally if needed
            if insight:
                story.append(Spacer(1, 2 * mm))
                label_w = 90
                value_w = content_w - label_w
                insight_rows = []
                if insight.get("summary"):
                    insight_rows.append([
                        Paragraph("Summary", ParagraphStyle("il", fontName="Helvetica-Bold", fontSize=8, textColor=NAVY)),
                        Paragraph(str(insight["summary"]), ParagraphStyle("iv", fontName="Helvetica", fontSize=8, textColor=CHARCOAL, leading=12)),
                    ])
                if insight.get("business_impact"):
                    insight_rows.append([
                        Paragraph("Business Impact", ParagraphStyle("il", fontName="Helvetica-Bold", fontSize=8, textColor=NAVY)),
                        Paragraph(str(insight["business_impact"]), ParagraphStyle("iv", fontName="Helvetica", fontSize=8, textColor=CHARCOAL, leading=12)),
                    ])
                if insight.get("recommendation"):
                    insight_rows.append([
                        Paragraph("Recommendation", ParagraphStyle("il", fontName="Helvetica-Bold", fontSize=8, textColor=NAVY)),
                        Paragraph(str(insight["recommendation"]), ParagraphStyle("iv", fontName="Helvetica", fontSize=8, textColor=CHARCOAL, leading=12)),
                    ])

                if insight_rows:
                    insight_tbl = Table(insight_rows, colWidths=[label_w, value_w], hAlign="LEFT")
                    insight_tbl.setStyle(TableStyle([
                        ("BACKGROUND",   (0, 0), (0, -1), BLUE_LIGHT),
                        ("TOPPADDING",   (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
                        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
                        ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#BFDBFE")),
                    ]))
                    story.append(insight_tbl)

            story.append(Spacer(1, 10 * mm))

    # ------------------------------------------------------------------
    # 6. KEY FINDINGS
    # ------------------------------------------------------------------
    if insights:
        story += _section("KEY FINDINGS")
        for ins in insights:
            story.append(Paragraph(f"• {ins}", styles["bullet"]))
        story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------
    # 7. BUSINESS RISKS
    # ------------------------------------------------------------------
    risks = bctx.get("risks", [])
    if risks:
        story += _section("BUSINESS RISKS")
        priorities = ["High", "Medium", "Low"]
        risk_styles = {
            "High":   styles["risk_high"],
            "Medium": styles["risk_medium"],
            "Low":    styles["risk_low"],
        }
        for i, risk in enumerate(risks):
            level = priorities[min(i, len(priorities) - 1)]
            label_sty = risk_styles.get(level, styles["bold"])
            story.append(KeepTogether([
                Paragraph(f"[{level}]", label_sty),
                Paragraph(risk, styles["body_small"]),
                Spacer(1, 3 * mm),
            ]))

    # ------------------------------------------------------------------
    # 8. GROWTH OPPORTUNITIES
    # ------------------------------------------------------------------
    opportunities = bctx.get("opportunities", [])
    if opportunities:
        story += _section("GROWTH OPPORTUNITIES")
        for opp in opportunities:
            story.append(Paragraph(f"• {opp}", styles["bullet"]))
        story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------
    # 9. RECOMMENDED ACTIONS
    # ------------------------------------------------------------------
    actions = bctx.get("priority_actions", [])
    if actions:
        story += _section("RECOMMENDED ACTIONS")
        story.append(Paragraph(
            "Prioritised action plan derived from analytics, KPI signals, and anomaly detection.",
            styles["section_intro"]
        ))

        action_data = [["Priority", "Action", "Reason"]]
        for act in actions:
            p = act.get("priority", "Medium")
            action_data.append([p, act.get("title", ""), act.get("reason", "")])

        content_w_act = W - 2 * MARGIN
        action_tbl = Table(
            action_data,
            colWidths=[55, 165, content_w_act - 55 - 165],
            hAlign="LEFT",
            repeatRows=1,
        )
        priority_colors = {"High": RED, "Medium": AMBER, "Low": GREEN}
        tbl_style = [
            ("BACKGROUND",   (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0), 9),
            ("TOPPADDING",   (0, 0), (-1, 0), 7),
            ("BOTTOMPADDING",(0, 0), (-1, 0), 7),
            ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",     (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [SLATE_LIGHT, WHITE]),
            ("TOPPADDING",   (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 1), (-1, -1), 5),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
        ]
        for row_i, row in enumerate(action_data[1:], start=1):
            p = row[0]
            col = priority_colors.get(p, SLATE)
            tbl_style.append(("TEXTCOLOR", (0, row_i), (0, row_i), col))
            tbl_style.append(("FONTNAME",  (0, row_i), (0, row_i), "Helvetica-Bold"))
        action_tbl.setStyle(TableStyle(tbl_style))
        story.append(action_tbl)
        story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------
    # 10. NEXT STEPS
    # ------------------------------------------------------------------
    next_steps = takeaways  # reuse CEO briefing key takeaways as next steps
    strengths  = bctx.get("strengths", [])
    rec_qs     = bctx.get("recommended_questions", [])

    if strengths or rec_qs:
        story += _section("NEXT STEPS & STRATEGIC QUESTIONS")
        if strengths:
            story.append(Paragraph("<b>Strengths to Leverage</b>", styles["bold"]))
            for s in strengths:
                story.append(Paragraph(f"• {s}", styles["bullet"]))
            story.append(Spacer(1, 3 * mm))
        if rec_qs:
            story.append(Paragraph("<b>Recommended Analytical Questions</b>", styles["bold"]))
            for q in rec_qs:
                story.append(Paragraph(f"• {q}", styles["bullet"]))
        story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------
    # 11. APPENDIX
    # ------------------------------------------------------------------
    story += _section("APPENDIX")

    appendix_rows = [
        ("Analysis Timestamp",  ts_str),
        ("Dataset ID",          dataset_id),
        ("InsightPilot Version","0.1.0"),
        ("PDF Generated",       datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
    ]
    story.append(_kv_table(appendix_rows))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "<i>This report was automatically generated by InsightPilot AI. "
        "All analysis is based solely on the uploaded dataset. "
        "This report does not constitute financial, legal, or professional advice. "
        "Always validate key findings against additional data sources before making business decisions.</i>",
        styles["body_small"],
    ))

    # =========================================================================
    # Build
    # =========================================================================
    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _section(title: str) -> list:
    return [ColorBar(title), Spacer(1, 4 * mm)]


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    """Two-column label/value table."""
    data = [[Paragraph(k, ParagraphStyle("kl", fontName="Helvetica", fontSize=8,
                                          textColor=SLATE)),
             Paragraph(str(v), ParagraphStyle("kv", fontName="Helvetica-Bold",
                                               fontSize=9, textColor=CHARCOAL))]
            for k, v in rows]
    tbl = Table(data, colWidths=[130, None], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [SLATE_LIGHT, WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _split_paragraphs(text: str, max_chars: int = 600) -> list[str]:
    """Split long text into readable paragraph chunks."""
    sentences = text.replace(". ", ".|").replace(".\n", "|\n").split("|")
    paragraphs, chunk = [], ""
    for s in sentences:
        if len(chunk) + len(s) > max_chars and chunk:
            paragraphs.append(chunk.strip())
            chunk = s + ". "
        else:
            chunk += s + ". "
    if chunk.strip():
        paragraphs.append(chunk.strip())
    return paragraphs or [text]
