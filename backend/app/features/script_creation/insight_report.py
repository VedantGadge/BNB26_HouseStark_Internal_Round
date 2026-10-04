"""PDF presentation for completed, evidence-backed insight jobs."""

import re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _text(value: object) -> str:
    return escape(str(value if value is not None else "Unavailable")).replace("\n", "<br/>")


def _number(value: object) -> str:
    return f"{value:,}" if isinstance(value, int | float) else "Unavailable"


def _percentage(value: object) -> str:
    return f"{value * 100:.2f}%" if isinstance(value, int | float) else "Unavailable"


def _duration(value: object) -> str:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", str(value or ""))
    if not match:
        return "its current duration"
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " and ".join(parts) or "its current duration"


def _ai_perspective(observation: dict) -> tuple[list[str], list[str]]:
    title = observation.get("title") or "this vertical video"
    duration = _duration(observation.get("duration"))
    views = observation.get("views")
    likes = observation.get("likes")
    comments = observation.get("comments")
    interaction = (
        f"The visible response is weighted toward likes ({_number(likes)}) "
        f"rather than comments ({_number(comments)}), so this snapshot captures "
        "lightweight audience approval more clearly "
        "than conversation."
        if isinstance(likes, int) and isinstance(comments, int)
        else "The available public response is incomplete, so audience interaction "
        "should be treated "
        "as directional only."
    )
    scale = (
        f"With {_number(views)} lifetime views, '{title}' is a useful creative "
        "reference, but channel "
        "size and cumulative distribution make it unsuitable as a direct benchmark for a new post."
        if isinstance(views, int)
        else f"'{title}' should be used as a creative reference, not a performance benchmark."
    )
    return (
        [
            f"This reel-style Short runs for {duration}; review its opening, pacing "
            "and payoff as one "
            "creative package rather than attributing reach to a single moment.",
            interaction,
            scale,
        ],
        [
            "Create two versions around the same idea: one with a direct first-second "
            "claim and one "
            "with a curiosity-led opening.",
            "Keep format and topic comparable, then measure at least three posts on the same 7-day "
            "owner-analytics window before choosing a direction.",
            "Use comments and retention from your connected channel to decide whether "
            "viewers are only "
            "reacting or staying through the full story.",
        ],
    )


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#D9DEE8"))
    canvas.line(18 * mm, 16 * mm, A4[0] - 18 * mm, 16 * mm)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18 * mm, 10 * mm, "CreatorAI - evidence-backed AI insight report")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def build_insight_report(facts: dict, result: dict) -> bytes:
    """Render only the frozen facts and validated model result retained by the job."""
    performance = facts.get("performance") or []
    if not isinstance(performance, list) or not performance:
        raise ValueError("Insight report has no performance evidence.")
    observation = performance[0]
    if not isinstance(observation, dict):
        raise ValueError("Insight report has invalid performance evidence.")

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=29,
        textColor=colors.HexColor("#11213A"),
        spaceAfter=4,
    )
    eyebrow = ParagraphStyle(
        "Eyebrow",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#F05A40"),
        spaceAfter=8,
    )
    section = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#11213A"),
        spaceBefore=16,
        spaceAfter=7,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#344054"),
    )
    metric_label = ParagraphStyle(
        "MetricLabel",
        parent=body,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#475467"),
    )
    metric_value = ParagraphStyle(
        "MetricValue",
        parent=body,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#11213A"),
    )

    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=24 * mm,
        title="CreatorAI AI Insight Report",
        author="CreatorAI",
    )
    story = [
        Paragraph("CREATORAI", eyebrow),
        Paragraph("AI insight report", title),
        Paragraph(
            _text(
                f"{observation.get('title', 'YouTube publication')} - "
                f"{observation.get('channel_title', 'Public channel')}"
            ),
            body,
        ),
        Spacer(1, 10),
        Paragraph("Executive summary", section),
        Paragraph(_text(result.get("summary", "")), body),
        Paragraph("Performance snapshot", section),
    ]
    metrics = [
        ("Video views", _number(observation.get("views"))),
        ("Likes", _number(observation.get("likes"))),
        ("Comments", _number(observation.get("comments"))),
        ("Engagement", _percentage(observation.get("engagement_rate"))),
    ]
    if observation.get("favorites") is not None:
        metrics.append(("Favorites (legacy)", _number(observation.get("favorites"))))
    channel = observation.get("channel_statistics") or {}
    if isinstance(channel, dict):
        if channel.get("subscribers_hidden"):
            metrics.append(("Channel subscribers", "Hidden"))
        else:
            metrics.append(("Channel subscribers", _number(channel.get("subscribers"))))
        metrics.extend(
            [
                ("Channel views", _number(channel.get("views"))),
                ("Channel videos", _number(channel.get("videos"))),
            ]
        )
    table = Table(
        [
            [Paragraph(_text(label), metric_label), Paragraph(_text(value), metric_value)]
            for label, value in metrics
        ],
        colWidths=[105 * mm, 65 * mm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FA")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9DEE8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E7EAF0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    ai_perspective, next_tests = _ai_perspective(observation)
    story.extend([table, Paragraph("AI perspective", section)])
    for item in ai_perspective:
        story.append(Paragraph(f"- {_text(item)}", body))
    story.extend([PageBreak(), Paragraph("Next creative tests", section)])
    for item in next_tests:
        story.append(Paragraph(f"- {_text(item)}", body))
    story.append(Paragraph("Evidence and limits", section))
    evidence = [
        f"Snapshot: {observation.get('snapshot_id', 'Unavailable')}",
        f"Observed: {observation.get('observed_at', 'Unavailable')}",
        f"Source: {observation.get('source', 'Unavailable')}",
    ]
    for item in evidence:
        story.append(Paragraph(f"- {_text(item)}", body))
    for item in result.get("limitations", []):
        story.append(Paragraph(f"- {_text(item)}", body))
    for item in facts.get("missing_data", []):
        story.append(Paragraph(f"- {_text(item)}", body))

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return stream.getvalue()
