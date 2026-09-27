"""Produce the report's scientific figures directly from saved checkpoints."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
with (ROOT / "analysis/learning_curves.csv").open() as f:
    ROWS = list(csv.DictReader(f))
COLORS = {"A_constant": "#176B91", "B_decay": "#BA4B24", "B_restored": "#5D438C",
          "fresh_constant": "#207553", "fresh_aged": "#666666"}
LABELS = {"A_constant": "A  constant rate", "B_decay": "B  decreasing rate",
          "B_restored": "B  rate restored", "fresh_constant": "Fresh  constant rate",
          "fresh_aged": "Fresh  aged schedule"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.labelcolor": "#222222",
                     "axes.titlesize": 11, "legend.fontsize": 9, "savefig.facecolor": "white"})


def curve(ax, arm, phase, metric, label=None, style="-", scale=100, shift=0):
    rows = [r for r in ROWS if r["arm"] == arm and r["phase"] == phase]
    steps = sorted({int(r["step"]) for r in rows})
    values = np.array([[float(r[metric]) for r in rows if int(r["step"]) == step] for step in steps]) * scale
    avg = values.mean(axis=1)
    sem95 = 1.96 * values.std(axis=1, ddof=1) / np.sqrt(values.shape[1])
    x = np.array(steps) + shift
    color = COLORS[arm]
    ax.plot(x, avg, color=color, lw=2.0, linestyle=style, label=label or LABELS[arm])
    ax.fill_between(x, avg - sem95, avg + sem95, color=color, alpha=0.12)


def tidy(ax, ylabel="Accuracy (%)", xlabel="Mini-batch updates after the change"):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color="#E4E7EA", linewidth=0.7)
    ax.set_axisbelow(True)


def main():
    folder = ROOT / "figures"
    folder.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 3.7), layout="constrained")
    for arm in ("A_constant", "B_decay"):
        curve(axes[0], arm, "pre", "acc_old", shift=-600)
        curve(axes[0], arm, "post", "acc_new", label="_nolegend_")
        curve(axes[1], arm, "post", "acc_old", label=LABELS[arm] + "  old rule")
        curve(axes[1], arm, "post", "acc_compatible", label=LABELS[arm] + "  compatible", style="--")
    axes[0].axvline(0, color="#666666", lw=1.0, linestyle=":")
    axes[0].text(8, 85, "Target change", rotation=90, va="center", fontsize=8.5, color="#555555")
    axes[0].set_title("a   Accuracy on the current task")
    axes[0].set_ylim(45, 102)
    axes[0].set_xticks([-600, -400, -200, 0, 200, 400])
    tidy(axes[0], xlabel="Updates relative to the target change")
    axes[0].legend(loc="lower left", frameon=False)
    axes[1].set_title("b   Retention after the change")
    axes[1].set_ylim(45, 102)
    tidy(axes[1])
    axes[1].legend(loc="center right", frameon=False, fontsize=8.5)
    fig.savefig(folder / "learning_and_retention.png", dpi=240)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 3.8), layout="constrained")
    for arm in COLORS:
        curve(axes[0], arm, "post", "acc_new", style="--" if arm.startswith("fresh") else "-")
        curve(axes[1], arm, "post", "loss_new", style="--" if arm.startswith("fresh") else "-", scale=1)
    axes[0].axhline(90, color="#999999", linestyle=":", lw=1)
    axes[0].text(215, 90.8, "90% threshold", fontsize=8.5, color="#555555")
    axes[0].set_title("a   New-task learning")
    axes[0].set_ylim(45, 103)
    axes[0].legend(loc="center right", frameon=False, fontsize=8)
    axes[1].set_title("b   New-task cross-entropy")
    tidy(axes[0])
    tidy(axes[1], ylabel="Mean cross-entropy (lower is better)")
    fig.savefig(folder / "adaptation_controls.png", dpi=240)
    plt.close(fig)
    print("Saved two figures from the 30-seed learning-curve CSV.")


if __name__ == "__main__":
    main()
