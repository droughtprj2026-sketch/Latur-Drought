# -*- coding: utf-8 -*-
"""Matplotlib / Seaborn publication styling and a single save-and-register helper."""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from . import config as C
from . import report

warnings.filterwarnings("ignore", category=FutureWarning)

# --------------------------------------------------------------------------
# Global style
# --------------------------------------------------------------------------
def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": C.DPI,
            "savefig.bbox": "tight",
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "mathtext.fontset": "cm",
            "font.size": 10.5,
            "axes.titlesize": 12.0,
            "axes.titleweight": "bold",
            "axes.labelsize": 11.0,
            "axes.edgecolor": "#1F2937",
            "axes.linewidth": 1.0,
            "axes.grid": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": "#E5E7EB",
            "grid.linestyle": ":",
            "grid.linewidth": 0.7,
            "grid.alpha": 0.7,
            "legend.frameon": True,
            "legend.framealpha": 0.95,
            "legend.edgecolor": "#9CA3AF",
            "legend.fontsize": 9.5,
            "xtick.labelsize": 10.0,
            "ytick.labelsize": 10.0,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.major.size": 4.5,
            "ytick.major.size": 4.5,
            "xtick.major.width": 0.9,
            "ytick.major.width": 0.9,
        }
    )


LATEX_LABELS = {
    "Rain_mm": r"$\mathrm{Precipitation}\;(\mathrm{mm})$",
    "SPI1": r"$\mathrm{SPI}_{1}$",
    "SPI3": r"$\mathrm{SPI}_{3}$",
    "SPI6": r"$\mathrm{SPI}_{6}$",
    "SPI12": r"$\mathrm{SPI}_{12}$",
    "NDVI": r"$\mathrm{NDVI}$",
    "EVI": r"$\mathrm{EVI}$",
    "VCI": r"$\mathrm{VCI}\;(\%)$",
    "VHI": r"$\mathrm{VHI}\;(\%)$",
    "NSMI": r"$\mathrm{NSMI}$",
    "composite_drought_score": r"$\mathrm{CDI}$",
}


def label_of(column: str) -> str:
    """Return LaTeX-rendered publication label or fall back to config."""
    if column in LATEX_LABELS:
        return LATEX_LABELS[column]
    spec = C.COL.get(column)
    return spec.label if spec else column


# Named colour ramps reused across the suite.
CDI_CMAP = LinearSegmentedColormap.from_list(
    "cdi_severity", ["#E2DED2", "#F2E26B", "#F6BC63", "#E9822F", "#C23B22", "#6E1423"]
)
COVERAGE_CMAP = LinearSegmentedColormap.from_list(
    "coverage", ["#F7F7F7", "#D9E8F5", "#8FBFE0", "#3C7FB3", "#17405F"]
)
RAIN_CMAP = LinearSegmentedColormap.from_list(
    "rain", ["#F5F5F5", "#C8E6F0", "#7FC7E0", "#2E86AB", "#0B3C5D"]
)
VEG_CMAP = LinearSegmentedColormap.from_list(
    "vegetation", ["#F4F1E8", "#D9E4B8", "#8CBF74", "#3E8E41", "#14532D"]
)
SOIL_CMAP = LinearSegmentedColormap.from_list(
    "soil", ["#FBF3E4", "#E8D3A9", "#C9A25A", "#8C6D31", "#4A3416"]
)
DIVERGING = "RdBu_r"
SEQUENTIAL = "viridis"

GROUP_CMAP = {
    "meteorological": RAIN_CMAP,
    "soil": SOIL_CMAP,
    "vegetation": VEG_CMAP,
    "composite": CDI_CMAP,
}


def cmap_for(column: str):
    spec = C.COL.get(column)
    if spec is None:
        return SEQUENTIAL
    return GROUP_CMAP.get(spec.group, SEQUENTIAL)


# --------------------------------------------------------------------------
# Save / register
# --------------------------------------------------------------------------
def save(fig, section: str, filename: str, caption: str, source: str = "") -> Path:
    """Write a figure to its section folder and record it in the index."""
    out_dir = C.section_dir(section)
    path = out_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=C.DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    report.register(section=section, filename=filename, caption=caption, source=source, path=path)
    print(f"  [{section}] {filename}")
    return path


# --------------------------------------------------------------------------
# Annotation helpers
# --------------------------------------------------------------------------
def p_text(p: float) -> str:
    if not np.isfinite(p):
        return "p = n/a"
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.3f}"


def stats_box(ax, lines: list[str], loc: str = "upper left", fontsize: float = 8.0,
              alpha: float = 0.92) -> None:
    anchors = {
        "upper left": (0.03, 0.97, "left", "top"),
        "upper right": (0.97, 0.97, "right", "top"),
        "lower left": (0.03, 0.03, "left", "bottom"),
        "lower right": (0.97, 0.03, "right", "bottom"),
    }
    x, y, ha, va = anchors[loc]
    ax.text(
        x, y, "\n".join(lines), transform=ax.transAxes, ha=ha, va=va,
        fontsize=fontsize, family="monospace", linespacing=1.35,
        bbox=dict(boxstyle="round,pad=0.45", facecolor="white", edgecolor="#9E9E9E",
                  linewidth=0.7, alpha=alpha),
        zorder=10,
    )


def underline(ax, text: str, fontsize: float = 9) -> None:
    ax.set_title(text, fontsize=fontsize, weight="bold")


def significance_stars(p: float) -> str:
    if not np.isfinite(p):
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def annotate_max(ax, x, y, label: str, color: str = "#111111") -> None:
    ax.annotate(
        label, xy=(x, y), xytext=(6, 10), textcoords="offset points",
        fontsize=8, color=color, weight="bold",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=color, lw=0.6, alpha=0.85),
    )


def add_panel_label(ax, label: str = "(a)", x: float = -0.05, y: float = 1.04,
                    fontsize: float = 12.0) -> None:
    """Standard Nature/Elsevier publication subfigure tag: (a), (b), (c)..."""
    ax.text(
        x, y, label, transform=ax.transAxes,
        fontsize=fontsize, weight="bold", color="#111827",
        va="bottom", ha="right", zorder=15
    )


def add_north_arrow(ax, x: float = 0.93, y: float = 0.90, length: float = 0.08) -> None:
    """True cartographic North arrow with compass pointer."""
    ax.annotate(
        "N", xy=(x, y + length), xytext=(x, y),
        xycoords="axes fraction", textcoords="axes fraction",
        ha="center", va="bottom", fontsize=10.5, weight="bold", color="#111827",
        arrowprops=dict(
            arrowstyle="-|>,head_length=0.7,head_width=0.4",
            facecolor="#111827", edgecolor="#111827", lw=1.2
        ),
        zorder=12,
    )


def add_scale_bar(ax, length_km: float = 20.0, x: float = 0.06, y: float = 0.07) -> None:
    """Georeferenced scale bar for Latur latitude (~18.4 deg N)."""
    # 1 deg lon at 18.4 N is ~105.6 km
    deg_len = length_km / 105.6
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    span_x = xlim[1] - xlim[0]
    span_y = ylim[1] - ylim[0]
    if span_x <= 0 or span_y <= 0:
        return

    x0 = xlim[0] + x * span_x
    y0 = ylim[0] + y * span_y
    x1 = x0 + deg_len
    h = 0.012 * span_y

    # Segmented black / white scale bar
    mid = (x0 + x1) / 2.0
    ax.fill([x0, mid, mid, x0], [y0, y0, y0 + h, y0 + h], color="#111827", zorder=12)
    ax.fill([mid, x1, x1, mid], [y0, y0, y0 + h, y0 + h], color="#FFFFFF", edgecolor="#111827", lw=0.8, zorder=12)
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y0 + h, y0 + h, y0], color="#111827", lw=0.9, zorder=13)

    ax.text(x0, y0 - 0.005 * span_y, "0", ha="center", va="top", fontsize=8.0, color="#111827", weight="bold")
    ax.text(mid, y0 - 0.005 * span_y, f"{int(length_km/2)}", ha="center", va="top", fontsize=8.0, color="#111827", weight="bold")
    ax.text(x1, y0 - 0.005 * span_y, f"{int(length_km)} km", ha="center", va="top", fontsize=8.0, color="#111827", weight="bold")


def figure_note(fig, text: str, y: float = -0.02) -> None:
    """Small italic footnote under the figure (method / caveat)."""
    fig.text(0.5, y, text, ha="center", va="top", fontsize=7.2, style="italic", color="#555555")


def despine_all(axes) -> None:
    for ax in np.ravel(axes):
        ax.grid(False)
