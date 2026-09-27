"""Generate Quarto tables from the experiment summary; no manual result entry."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "analysis/summary.json").read_text())
A = S["arms"]


def mean(arm, metric, scale=1):
    return f"{A[arm][metric]['mean'] * scale:.2f}"


def recovery(arm):
    r = A[arm]["recovery"]
    if r["n_reached"] == 0:
        return ">400 (0/30)"
    return f"{r['median_among_reached']:g} ({r['n_reached']}/30)"


rows = [
    ("Old-task accuracy before change (%)", "acc_old_start", 100),
    ("New-task accuracy at change (%)", "acc_new_start", 100),
    ("New-task accuracy after 400 updates (%)", "acc_new_final", 100),
    ("Old-task accuracy after 400 updates (%)", "acc_old_final", 100),
    ("Early slope (pp per 100 updates)", "early_slope_pp_per_100", 1),
    ("Mean accuracy across new-task trajectory (%)", "mean_post_acc", 100),
]
lines = ["| Metric | A constant rate | B decreasing rate |", "|:--|--:|--:|"]
for label, key, scale in rows:
    lines.append(f"| {label} | {mean('A_constant', key, scale)} | {mean('B_decay', key, scale)} |")
lines.append(f"| Updates to sustained 90% (seeds reaching) | {recovery('A_constant')} | {recovery('B_decay')} |")
lines += ["", ": Main comparison across 30 paired runs {#tbl-main}", ""]
(ROOT / "analysis/main-table.md").write_text("\n".join(lines))

lines = ["| Condition | Final new-task accuracy (%) | Final cross-entropy | Updates to 90% |", "|:--|--:|--:|--:|"]
for arm, label in [("A_constant", "A constant rate"), ("B_decay", "B decreasing rate"),
                   ("B_restored", "B rate restored"), ("fresh_constant", "Fresh constant rate"),
                   ("fresh_aged", "Fresh aged schedule")]:
    lines.append(f"| {label} | {mean(arm, 'acc_new_final', 100)} | {A[arm]['loss_new_final']['mean']:.3f} | {recovery(arm)} |")
lines += ["", ": Controls under the same new-task training budget {#tbl-controls}", ""]
(ROOT / "analysis/control-table.md").write_text("\n".join(lines))
print("Generated two report tables from analysis/summary.json.")
