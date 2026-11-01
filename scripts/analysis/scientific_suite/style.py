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
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
            "font.size": 9.5,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.edgecolor": "#3A3A3A",
            "axes.linewidth": 0.8,
            "axes.grid": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": "#DFDFDF",
            "grid.linestyle": "--",
            "grid.linewidth": 0.6,
            "grid.alpha": 0.8,
            "legend.frameon": True,
            "legend.framealpha": 0.92,
            "legend.edgecolor": "#CCCCCC",
            "legend.fontsize": 8.5,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "xtick.direction": "out",
            "ytick.direction": "out",
        }
    )


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


def figure_note(fig, text: str, y: float = -0.02) -> None:
    """Small italic footnote under the figure (method / caveat)."""
    fig.text(0.5, y, text, ha="center", va="top", fontsize=7.2, style="italic", color="#555555")


def despine_all(axes) -> None:
    for ax in np.ravel(axes):
        ax.grid(False)
