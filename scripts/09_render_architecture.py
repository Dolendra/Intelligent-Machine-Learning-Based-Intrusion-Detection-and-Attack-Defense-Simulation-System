"""Render architecture diagram to PNG (GitHub-friendly) and clean SVG."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT_PNG = ROOT / "docs" / "architecture.png"
OUT_SVG = ROOT / "docs" / "architecture.svg"


def draw(ax):
    ax.set_xlim(0, 960)
    ax.set_ylim(0, 420)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("#07111a")
    fig = ax.figure
    fig.patch.set_facecolor("#07111a")

    def box(x, y, w, h, edge, title, lines, title_color):
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=12",
            linewidth=1.5,
            edgecolor=edge,
            facecolor="#122536",
        )
        ax.add_patch(patch)
        ax.text(x + 20, y + h - 28, title, color=title_color, fontsize=12, fontweight="bold", va="top")
        for i, line in enumerate(lines):
            ax.text(x + 20, y + h - 55 - i * 22, line, color="#8fa6b5", fontsize=10, va="top")

    ax.text(32, 390, "Aegis IDS - Architecture", color="#3ec7c2", fontsize=14, fontweight="bold")

    # UI
    box(40, 310, 880, 60, "#3ec7c2", "React UI", ["Dashboard · Detection · Simulation · Reports"], "#e7f0f5")
    ax.annotate("", xy=(480, 285), xytext=(480, 310), arrowprops=dict(arrowstyle="->", color="#8fa6b5", lw=1.5))

    # API
    box(
        40,
        210,
        880,
        55,
        "#e4a54a",
        "FastAPI",
        ["/predict · /explain · /risk · /recommendation · /simulation · /incidents"],
        "#e7f0f5",
    )
    ax.annotate("", xy=(180, 185), xytext=(180, 210), arrowprops=dict(arrowstyle="->", color="#8fa6b5", lw=1.2))
    ax.annotate("", xy=(480, 185), xytext=(480, 210), arrowprops=dict(arrowstyle="->", color="#8fa6b5", lw=1.2))
    ax.annotate("", xy=(780, 185), xytext=(780, 210), arrowprops=dict(arrowstyle="->", color="#8fa6b5", lw=1.2))

    box(40, 55, 280, 110, "#3ec7c2", "ML Engine", ["Preprocess · Features", "Binary + Multiclass"], "#3ec7c2")
    box(340, 55, 280, 110, "#e4a54a", "Security Engine", ["SHAP / LIME · Risk", "Recommendations"], "#e4a54a")
    box(640, 55, 280, 110, "#5ecf8a", "Simulation", ["Topology · Attack", "Defense · Recover"], "#5ecf8a")

    ax.text(32, 20, "Data: CICIDS2017 · trained models · SQLite incidents", color="#8fa6b5", fontsize=9)


def main() -> None:
    fig, ax = plt.subplots(figsize=(12, 5.25), dpi=160)
    draw(ax)
    fig.savefig(OUT_PNG, bbox_inches="tight", facecolor=fig.get_facecolor(), pad_inches=0.15)
    plt.close(fig)

    # Clean SVG (ASCII-safe) for optional local use
    OUT_SVG.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="960" height="420" viewBox="0 0 960 420">
  <rect width="960" height="420" fill="#07111a" rx="16"/>
  <text x="32" y="42" fill="#3ec7c2" font-family="Arial, sans-serif" font-size="18" font-weight="700">Aegis IDS - Architecture</text>
  <rect x="40" y="70" width="880" height="70" rx="12" fill="#122536" stroke="#3ec7c2"/>
  <text x="60" y="112" fill="#e7f0f5" font-family="Arial, sans-serif" font-size="18" font-weight="600">React UI - Dashboard | Detection | Simulation | Reports</text>
  <line x1="480" y1="140" x2="480" y2="168" stroke="#8fa6b5" stroke-width="2"/>
  <polygon points="480,175 474,165 486,165" fill="#8fa6b5"/>
  <rect x="40" y="175" width="880" height="60" rx="12" fill="#122536" stroke="#e4a54a"/>
  <text x="60" y="212" fill="#e7f0f5" font-family="Arial, sans-serif" font-size="16" font-weight="600">FastAPI - /predict /explain /risk /recommendation /simulation /incidents</text>
  <rect x="40" y="265" width="280" height="110" rx="12" fill="#122536" stroke="#3ec7c2"/>
  <text x="60" y="300" fill="#3ec7c2" font-family="Arial, sans-serif" font-size="16" font-weight="700">ML Engine</text>
  <text x="60" y="328" fill="#8fa6b5" font-family="Arial, sans-serif" font-size="14">Preprocess | Features</text>
  <text x="60" y="350" fill="#8fa6b5" font-family="Arial, sans-serif" font-size="14">Binary + Multiclass</text>
  <rect x="340" y="265" width="280" height="110" rx="12" fill="#122536" stroke="#e4a54a"/>
  <text x="360" y="300" fill="#e4a54a" font-family="Arial, sans-serif" font-size="16" font-weight="700">Security Engine</text>
  <text x="360" y="328" fill="#8fa6b5" font-family="Arial, sans-serif" font-size="14">SHAP / LIME | Risk</text>
  <text x="360" y="350" fill="#8fa6b5" font-family="Arial, sans-serif" font-size="14">Recommendations</text>
  <rect x="640" y="265" width="280" height="110" rx="12" fill="#122536" stroke="#5ecf8a"/>
  <text x="660" y="300" fill="#5ecf8a" font-family="Arial, sans-serif" font-size="16" font-weight="700">Simulation</text>
  <text x="660" y="328" fill="#8fa6b5" font-family="Arial, sans-serif" font-size="14">Topology | Attack</text>
  <text x="660" y="350" fill="#8fa6b5" font-family="Arial, sans-serif" font-size="14">Defense | Recover</text>
  <text x="32" y="405" fill="#8fa6b5" font-family="Arial, sans-serif" font-size="12">Data: CICIDS2017 | trained models | SQLite incidents</text>
</svg>
""",
        encoding="utf-8",
    )
    print(f"Wrote {OUT_PNG}")
    print(f"Wrote {OUT_SVG}")


if __name__ == "__main__":
    main()
