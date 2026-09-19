"""Renders an interview report as a downloadable PDF from the same data
the in-app report shows - the verdict, the five judged dimensions with
their cited evidence, and the phase-by-phase transcript.
"""

import io
from datetime import datetime
from xml.sax.saxutils import escape  # nosec B406

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

from app.constants.interview import PHASE_LABELS
from app.dto.interview import InterviewSessionDetail, TranscriptEntry
from app.dto.judge import InterviewReportResponse

INK = colors.HexColor("#122033")
MUTED = colors.HexColor("#627085")
NAVY = colors.HexColor("#173e6a")
HERO = colors.HexColor("#0a1730")
RULE = colors.HexColor("#d8e0ea")
BRAND_TEXT = colors.HexColor("#0d6b5f")
CITED_FILL = colors.HexColor("#ecfaf7")
CITED_BORDER = colors.HexColor("#8ed8cb")
MESSAGE_FILL = colors.HexColor("#f9fbfc")
WARNING_TEXT = colors.HexColor("#92400e")
WARNING_FILL = colors.HexColor("#fef3c7")
WARNING_BORDER = colors.HexColor("#f59e0b")

GOOD = colors.HexColor("#059669")
FAIR = colors.HexColor("#d97706")
POOR = colors.HexColor("#dc2626")
TIER_COLORS = {
    "strong_hire": GOOD,
    "hire": GOOD,
    "borderline": FAIR,
    "no_hire": POOR,
}
GOOD_SCORE = 70
FAIR_SCORE = 55

PAGE_MARGIN = 18 * mm
BOX_PADDING = 6
FRAME_WIDTH = A4[0] - 2 * PAGE_MARGIN

_STYLES = getSampleStyleSheet()
HEADING = ParagraphStyle(
    "Heading", parent=_STYLES["Heading2"], textColor=NAVY, spaceBefore=16, spaceAfter=4
)
SUBHEADING = ParagraphStyle(
    "Subheading",
    parent=_STYLES["Heading3"],
    textColor=INK,
    spaceBefore=10,
    spaceAfter=2,
)
BODY = ParagraphStyle("Body", parent=_STYLES["BodyText"], textColor=INK, leading=14)
HEADLINE = ParagraphStyle(
    "Headline", parent=BODY, fontSize=12, leading=17, spaceBefore=10, spaceAfter=6
)
CAPTION = ParagraphStyle("Caption", parent=BODY, textColor=MUTED, fontSize=9)
QUOTE = ParagraphStyle(
    "Quote", parent=BODY, textColor=MUTED, leftIndent=10, fontName="Helvetica-Oblique"
)
CALLOUT = ParagraphStyle(
    "Callout",
    parent=BODY,
    textColor=WARNING_TEXT,
    backColor=WARNING_FILL,
    borderColor=WARNING_BORDER,
    borderWidth=1,
    borderPadding=BOX_PADDING + 2,
    leftIndent=BOX_PADDING + 2,
    rightIndent=BOX_PADDING + 2,
    spaceBefore=12,
    spaceAfter=12,
)
VERDICT = ParagraphStyle(
    "Verdict",
    parent=BODY,
    textColor=colors.white,
    alignment=TA_CENTER,
    fontName="Helvetica-Bold",
    fontSize=15,
    leading=19,
)
BANNER_TITLE = ParagraphStyle(
    "BannerTitle",
    parent=BODY,
    textColor=colors.white,
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=24,
)
BANNER_SUBTITLE = ParagraphStyle(
    "BannerSubtitle", parent=BODY, textColor=colors.HexColor("#94a3b8"), fontSize=10
)


def _markup(text: str) -> str:
    """Text made safe for reportlab's paragraph markup, which would
    otherwise read transcript characters like < and & as tags.
    """
    return escape(text).replace("\n", "<br/>")


def _message_style(is_cited: bool) -> ParagraphStyle:
    """A transcript message drawn as a bordered card - a paragraph with a
    background and border, so a long message can still split across pages.
    """
    return ParagraphStyle(
        "CitedMessage" if is_cited else "Message",
        parent=BODY,
        backColor=CITED_FILL if is_cited else MESSAGE_FILL,
        borderColor=CITED_BORDER if is_cited else RULE,
        borderWidth=0.8,
        borderPadding=BOX_PADDING,
        leftIndent=BOX_PADDING,
        rightIndent=BOX_PADDING,
        spaceBefore=BOX_PADDING + 6,
        spaceAfter=BOX_PADDING + 6,
    )


def _score_color(score: float) -> colors.Color:
    if score >= GOOD_SCORE:
        return GOOD
    return FAIR if score >= FAIR_SCORE else POOR


def _format_date(value: datetime) -> str:
    return value.strftime("%d %b %Y")


def _banner(report: InterviewReportResponse, detail: InterviewSessionDetail) -> Table:
    """The top of the report: who and when on the left, the verdict and
    overall score on the right.
    """
    title = detail.job_role + (
        f" at {detail.company_name}" if detail.company_name else ""
    )
    left = [
        Paragraph("INTERVIEW REPORT", BANNER_SUBTITLE),
        Paragraph(_markup(title), BANNER_TITLE),
        Paragraph(f"Interviewed on {_format_date(detail.created_at)}", BANNER_SUBTITLE),
    ]
    verdict = Table(
        [
            [Paragraph(_markup(report.recommendation_label.upper()), VERDICT)],
            [Paragraph(f"{report.overall_score:.0f} / 100", VERDICT)],
        ],
        colWidths=[46 * mm],
    )
    verdict.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    TIER_COLORS.get(report.recommendation_tier, NAVY),
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    banner = Table([[left, verdict]], colWidths=[FRAME_WIDTH - 52 * mm, 52 * mm])
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HERO),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (-1, 0), (-1, 0), 12),
            ]
        )
    )
    return banner


def _overview_section(report: InterviewReportResponse) -> list:
    story = [Paragraph(_markup(report.headline), HEADLINE)]
    if report.end_reason_label:
        story.append(Paragraph(f"<b>{_markup(report.end_reason_label)}</b>", CALLOUT))

    facts = [f"Red flags recorded: {report.red_flag_count}"]
    if report.hint_counts:
        hints = ", ".join(
            f"{PHASE_LABELS.get(phase, phase)}: {count}"
            for phase, count in report.hint_counts.items()
        )
        facts.append(f"Hints given: {hints}")
    story.extend(Paragraph(_markup(fact), CAPTION) for fact in facts)
    return story


def _dimensions_section(report: InterviewReportResponse) -> list:
    story = [Paragraph("Scores by dimension", HEADING)]
    for evaluation in report.judge_evaluations:
        weight = report.weights_used.get(evaluation.judge_name, 0)
        color = _score_color(evaluation.score).hexval()[2:]
        story.append(
            Paragraph(
                f"{_markup(evaluation.dimension)} - "
                f'<font color="#{color}">{evaluation.score:.0f} / 100</font> '
                f'<font size="9" color="#627085">({weight:.0%} of overall)</font>',
                SUBHEADING,
            )
        )
        story.append(Paragraph(_markup(evaluation.summary), BODY))
        for item in evaluation.evidence:
            story.append(Paragraph(f"“{_markup(item.quote)}”", QUOTE))
            story.append(Paragraph(_markup(item.reasoning), CAPTION))
    return story


def _citations_by_index(
    report: InterviewReportResponse,
) -> dict[int, list[tuple[str, str]]]:
    """Judge evidence keyed by the transcript message it cites, as
    (dimension, reasoning) pairs.
    """
    by_index: dict[int, list[tuple[str, str]]] = {}
    for evaluation in report.judge_evaluations:
        for item in evaluation.evidence:
            if item.transcript_index is not None:
                by_index.setdefault(item.transcript_index, []).append(
                    (evaluation.dimension, item.reasoning)
                )
    return by_index


def _message_card(
    entry: TranscriptEntry, citations: list[tuple[str, str]]
) -> Paragraph:
    speaker = "INTERVIEWER" if entry.role == "model" else "YOU"
    hint = (
        f' <font color="#b45309">- hint {entry.hint_level}</font>'
        if entry.hint_level is not None
        else ""
    )
    lines = [
        f'<font size="8" color="#627085"><b>{speaker}</b>{hint}</font>',
        _markup(entry.text),
    ]
    lines.extend(
        f'<font size="9" color="#0d6b5f"><b>Cited for {_markup(dimension)}:</b> '
        f"{_markup(reasoning)}</font>"
        for dimension, reasoning in citations
    )
    return Paragraph("<br/>".join(lines), _message_style(bool(citations)))


def _transcript_section(
    report: InterviewReportResponse, detail: InterviewSessionDetail
) -> list:
    citations = _citations_by_index(report)
    story = [Paragraph("Transcript by phase", HEADING)]
    current_phase: str | None = None
    for entry in detail.transcript:
        if entry.phase != current_phase:
            current_phase = entry.phase
            story.append(HRFlowable(width="100%", color=RULE, spaceBefore=8))
            story.append(
                Paragraph(
                    _markup(PHASE_LABELS.get(current_phase or "", current_phase or "")),
                    SUBHEADING,
                )
            )
        story.append(_message_card(entry, citations.get(entry.index, [])))
    return story


def build_report_pdf(
    report: InterviewReportResponse, detail: InterviewSessionDetail
) -> bytes:
    """The finished report as PDF bytes."""
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Interview report",
    )
    document.build(
        [
            _banner(report, detail),
            *_overview_section(report),
            *_dimensions_section(report),
            *_transcript_section(report, detail),
        ]
    )
    return buffer.getvalue()
