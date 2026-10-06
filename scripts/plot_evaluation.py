"""Standalone held-out prediction plots; optional Matplotlib dependency."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter
import pandas as pd


def main():
    version = json.loads((ROOT / "models/current.json").read_text())["model_version"]
    folder = ROOT / "reports/phase2" / version
    rows = pd.read_csv(folder / "test_predictions.csv")
    evaluation = json.loads((folder / "evaluation.json").read_text())
    sources = {"nepal_user_2000": ("User CSV (origin unverified)", "#a26332"),
               "nepal_bikebazar_2025": ("Public Nepal listings", "#236192")}
    fig, axes = plt.subplots(1, 3, figsize=(14, 6.3))
    for ax, kind in zip(axes, ("Car", "Bike", "Scooter")):
        subset = rows.loc[rows.vehicle_type == kind]
        for source, (label, color) in sources.items():
            selected = subset.loc[subset.source_id == source]
            if not selected.empty:
                ax.scatter(selected.price, selected.predicted_price_npr, s=17, alpha=.6, color=color, label=label)
        lower = min(subset.price.min(), subset.predicted_price_npr.min()) * .8
        upper = max(subset.price.max(), subset.predicted_price_npr.max()) * 1.2
        ax.plot([lower, upper], [lower, upper], color="#555555", linewidth=1, linestyle="--")
        result = evaluation["models"][kind]["test"]
        ax.set(xscale="log", yscale="log", xlim=(lower, upper), ylim=(lower, upper),
               xlabel="Source price (NPR, log scale)", ylabel="Predicted price (NPR, log scale)",
               title=f"{kind} · n={len(subset)}\nR² {result['r2']:.3f} · MAE NPR {result['mae_npr']:,.0f}")
        ax.set_aspect("equal", adjustable="box")
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_locator(LogLocator(base=10, subs=(1, 2, 5)))
            axis.set_major_formatter(FuncFormatter(lambda value, position: f"{value / 1e6:g}m" if value >= 1e6 else f"{value / 1e3:g}k"))
            axis.set_minor_formatter(NullFormatter())
        ax.grid(alpha=.15)
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.5, .11), ncol=2, frameon=False)
    fig.suptitle(f"SmartSauda · Held-out test predictions · {version}", fontsize=16, fontweight="bold")
    fig.text(.5, .055, "Dashed line: exact prediction. Car results use only the unverified user source; these are dataset metrics.", ha="center", fontsize=10)
    fig.subplots_adjust(left=.055, right=.985, bottom=.27, top=.84, wspace=.38)
    fig.savefig(folder / "test-predictions.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
