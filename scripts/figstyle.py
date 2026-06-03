"""QFIRE figure design system.

Import this and call ``figstyle.apply()`` at the top of every plot script so the
whole figure set shares one palette, one type scale, and one grid style. Use the
colour constants below instead of ad-hoc hex so QFIRE is the *same* accent in
every figure (readers learn ``blue = QFIRE``), baselines are neutral grey, and
attack/danger is red.

Nothing here touches the data — it is purely presentation.
"""
import matplotlib as mpl

# ---- palette -------------------------------------------------------------
QFIRE      = "#1E6FBF"   # the QFIRE accent — QFIRE's bar/point/line everywhere
QFIRE_DARK = "#123F75"
ACCENT     = "#EE9B33"   # secondary accent (amber) — highlights / "holds"
ACCENT_DK  = "#B9740F"
BASELINE   = "#9AA7B8"   # neutral grey — baselines / "off"
BASELINE_D = "#6E7B8C"
BAD        = "#C9402F"   # attack success / harm / "no firewall"
GOOD       = "#1E8A5B"   # allow / safe / contained
INK        = "#1A2230"   # primary text
MUTED      = "#8390A2"   # secondary text / faint elements
HILITE     = "#FCEFDC"   # soft amber fill to spotlight the punchline element

# diverging map for the recall heatmap (red = missed, green = blocked)
HEAT_CMAP = "RdYlGn"


def apply():
    mpl.rcParams.update({
        "figure.dpi": 230, "savefig.dpi": 230,
        "savefig.bbox": "tight", "figure.facecolor": "white",
        "font.family": "DejaVu Sans", "font.size": 13.5,
        "text.color": INK,
        "axes.facecolor": "white",
        "axes.edgecolor": "#AEB7C4", "axes.linewidth": 1.1,
        "axes.titlesize": 15.5, "axes.titleweight": "bold", "axes.titlepad": 10,
        "axes.labelsize": 13.5, "axes.labelcolor": INK, "axes.labelpad": 6,
        "axes.titlecolor": INK,
        "xtick.labelsize": 12, "ytick.labelsize": 12,
        "xtick.color": INK, "ytick.color": INK,
        "xtick.major.size": 4, "ytick.major.size": 4,
        "legend.fontsize": 12, "legend.frameon": True, "legend.framealpha": 0.96,
        "legend.edgecolor": "#D3D8E0", "legend.borderpad": 0.6,
        "axes.grid": True, "axes.axisbelow": True,
        "grid.color": "#E4E1D9", "grid.linewidth": 0.9, "grid.alpha": 1.0,
        "lines.linewidth": 2.4, "lines.markersize": 9,
    })


def despine(ax, keep=("left", "bottom")):
    """Hide all but the kept spines (default: clean L-frame)."""
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(s in keep)


def value_label(ax, x, y, text, color=INK, dy=0.018, **kw):
    """Bold value label above a bar/point."""
    ax.text(x, y + dy, text, ha="center", va="bottom",
            fontsize=kw.pop("fontsize", 13), fontweight="bold", color=color, **kw)
