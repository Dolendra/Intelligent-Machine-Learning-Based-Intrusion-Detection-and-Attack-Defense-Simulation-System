"""PDF analytics report builder (matplotlib Agg + PdfPages)."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402


def build_analytics_pdf(payload: dict[str, Any]) -> bytes:
    analytics = payload.get("analytics") or {}
    incidents = payload.get("incidents") or []
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig = plt.figure(figsize=(8.5, 11))
        fig.patch.set_facecolor("white")
        fig.text(0.08, 0.92, "Aegis IDS — Analytics Report", fontsize=18, weight="bold")
        fig.text(0.08, 0.88, "Decision-support prototype export (not live packet capture)", fontsize=9, color="#444444")
        fig.text(
            0.08,
            0.84,
            f"Generated: {payload.get('exported_at') or datetime.now(timezone.utc).isoformat()}",
            fontsize=9,
        )
        total = analytics.get("total_incidents", 0)
        lines = [f"Total incidents: {total}", "", "By severity:"]
        for k, v in sorted((analytics.get("by_severity") or {}).items()):
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("By attack type:")
        for k, v in sorted((analytics.get("by_attack_type") or {}).items()):
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("By status:")
        for k, v in sorted((analytics.get("by_status") or {}).items()):
            lines.append(f"  {k}: {v}")
        fig.text(0.08, 0.78, "\n".join(lines), fontsize=10, family="monospace", va="top")
        fig.text(
            0.08,
            0.08,
            "Recommendations shown in the platform are advisory only.\n"
            "This PDF summarizes persisted incident analytics for viva/reporting.",
            fontsize=8,
            color="#555555",
        )
        pdf.savefig(fig)
        plt.close(fig)

        rows = incidents[:40]
        fig = plt.figure(figsize=(8.5, 11))
        fig.patch.set_facecolor("white")
        fig.text(0.08, 0.94, "Recent incidents (up to 40)", fontsize=14, weight="bold")
        table_data = [["ID", "Attack", "Severity", "Risk", "Status"]]
        for item in rows:
            table_data.append(
                [
                    str(item.get("incident_id", ""))[:12],
                    str(item.get("attack_type", ""))[:12],
                    str(item.get("severity", ""))[:10],
                    str(item.get("risk_score", "")),
                    str(item.get("status", ""))[:14],
                ]
            )
        if len(table_data) == 1:
            table_data.append(["—", "—", "—", "—", "—"])
        ax = fig.add_axes([0.05, 0.08, 0.9, 0.8])
        ax.axis("off")
        table = ax.table(cellText=table_data, loc="upper center", cellLoc="left")
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.3)
        pdf.savefig(fig)
        plt.close(fig)

    return buf.getvalue()
