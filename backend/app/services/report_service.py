"""Monthly executive report generator — PDF via ReportLab.

Generates a branded PDF with KPIs, team stats, and ROI for a given month.
Stores the PDF in the uploads directory and optionally sends via email.
"""

import io
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import case, cast, Float, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.ai_usage import AIUsageLog
from app.models.asset import AssetStatus, MediaAsset
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger("bluewave.reports")

REPORTS_DIR = "/app/uploads/reports"


async def _gather_month_data(tenant_id: uuid.UUID, month_start: datetime, month_end: datetime) -> dict:
    """Gather all analytics data for a single month."""
    async with async_session_factory() as db:
        # Asset stats
        asset_result = await db.execute(
            select(
                func.count(MediaAsset.id).label("total"),
                func.count(case((MediaAsset.status == AssetStatus.approved, 1))).label("approved"),
                func.avg(
                    case((MediaAsset.compliance_score.isnot(None), cast(MediaAsset.compliance_score, Float)))
                ).label("avg_compliance"),
            ).where(
                MediaAsset.tenant_id == tenant_id,
                MediaAsset.created_at >= month_start,
                MediaAsset.created_at < month_end,
            )
        )
        row = asset_result.one()

        # AI usage
        ai_result = await db.execute(
            select(
                func.count(AIUsageLog.id),
                func.coalesce(func.sum(AIUsageLog.cost_millicents), 0),
            ).where(
                AIUsageLog.tenant_id == tenant_id,
                AIUsageLog.created_at >= month_start,
                AIUsageLog.created_at < month_end,
            )
        )
        ai_row = ai_result.one()

        # Team stats
        team_result = await db.execute(
            select(
                User.full_name,
                func.count(MediaAsset.id).label("uploads"),
            )
            .outerjoin(MediaAsset, (MediaAsset.uploaded_by == User.id) & (MediaAsset.created_at >= month_start) & (MediaAsset.created_at < month_end))
            .where(User.tenant_id == tenant_id)
            .group_by(User.id, User.full_name)
            .order_by(func.count(MediaAsset.id).desc())
        )
        team = [(r.full_name, r.uploads) for r in team_result.all()]

        # Tenant name
        tenant_result = await db.execute(select(Tenant.name).where(Tenant.id == tenant_id))
        tenant_name = tenant_result.scalar() or "Unknown"

    assets_processed = ai_row[0] or 0
    hours_saved = round(assets_processed * 14.5 / 60, 1)

    return {
        "tenant_name": tenant_name,
        "total_assets": row.total or 0,
        "total_approved": row.approved or 0,
        "avg_compliance": round(float(row.avg_compliance), 1) if row.avg_compliance else None,
        "ai_actions": ai_row[0] or 0,
        "ai_cost_usd": round(float(ai_row[1] or 0) / 100_000, 2),
        "hours_saved": hours_saved,
        "cost_saved_usd": round(hours_saved * 45, 2),
        "team": team,
    }


def _build_pdf(data: dict, month_label: str) -> bytes:
    """Build a PDF report and return the bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Heading1"], fontSize=22, textColor=colors.HexColor("#2563EB"))
    subtitle_style = ParagraphStyle("ReportSubtitle", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#6B7280"))
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=16, textColor=colors.HexColor("#1F2937"), spaceBefore=20)

    elements = []

    # Header
    elements.append(Paragraph("Bluewave", title_style))
    elements.append(Paragraph(f"Monthly Report — {month_label}", subtitle_style))
    elements.append(Paragraph(f"Organization: {data['tenant_name']}", styles["Normal"]))
    elements.append(Spacer(1, 1 * cm))

    # KPIs
    elements.append(Paragraph("Key Metrics", section_style))
    kpi_data = [
        ["Metric", "Value"],
        ["Total Assets Uploaded", str(data["total_assets"])],
        ["Assets Approved", str(data["total_approved"])],
        ["Avg Compliance Score", str(data["avg_compliance"]) if data["avg_compliance"] else "N/A"],
        ["AI Actions Used", str(data["ai_actions"])],
        ["AI Cost", f"${data['ai_cost_usd']:.2f}"],
    ]
    kpi_table = Table(kpi_data, colWidths=[10 * cm, 6 * cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.5 * cm))

    # ROI
    elements.append(Paragraph("Estimated ROI", section_style))
    elements.append(Paragraph(
        f"Bluewave saved your team an estimated <b>{data['hours_saved']} hours</b> "
        f"and <b>${data['cost_saved_usd']:,.2f}</b> this month "
        f"(based on $45/hr industry benchmark, 15 min manual vs 30 sec AI per asset).",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 0.5 * cm))

    # Team
    if data["team"]:
        elements.append(Paragraph("Team Activity", section_style))
        team_data = [["Team Member", "Uploads"]]
        for name, uploads in data["team"]:
            team_data.append([name, str(uploads)])
        team_table = Table(team_data, colWidths=[10 * cm, 6 * cm])
        team_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(team_table)

    # Footer
    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph(
        f"Generated by Bluewave on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#9CA3AF")),
    ))

    doc.build(elements)
    return buf.getvalue()


async def generate_monthly_report(
    tenant_id: uuid.UUID,
    year: int,
    month: int,
) -> str:
    """Generate a monthly PDF report. Returns the file path."""
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    month_label = month_start.strftime("%B %Y")

    data = await _gather_month_data(tenant_id, month_start, month_end)
    pdf_bytes = _build_pdf(data, month_label)

    # Save
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = f"bluewave_report_{tenant_id}_{year}_{month:02d}.pdf"
    file_path = os.path.join(REPORTS_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    logger.info("Report generated: %s (%d bytes)", file_path, len(pdf_bytes))
    return file_path
