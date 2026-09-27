"""Independent numerical checks plus reproducibility and report consistency."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
from run_experiment import update

ROOT = Path(__file__).resolve().parents[1]
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def read_csv(name):
    with (ROOT / "analysis" / name).open() as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_gradient():
    rng = np.random.default_rng(735)
    x = np.column_stack([rng.normal(size=(13, 2)), np.ones(13)])
    y = rng.integers(0, 2, size=13)
    w = np.array([0.35, -0.8, 0.1])
    l2 = 0.03
    def objective(v):
        z = x @ v
        return np.mean(np.logaddexp(0, z) - y * z) + l2 * (v[:2] @ v[:2]) / 2
    analytic = w - update(w.copy(), x, y, 1, l2)
    numerical = []
    for i in range(3):
        e = np.zeros(3)
        e[i] = 1e-6
        numerical.append((objective(w + e) - objective(w - e)) / 2e-6)
    np.testing.assert_allclose(analytic, numerical, atol=1e-8, rtol=1e-7)
    return float(np.max(np.abs(analytic - numerical)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args()
    config = json.loads((ROOT / "config.json").read_text())
    agg = json.loads((ROOT / "analysis/summary.json").read_text())
    curves = read_csv("learning_curves.csv")
    per_seed = read_csv("per_seed_metrics.csv")
    manifest = read_csv("dataset_manifest.csv")
    records = {}
    for row in curves:
        key = int(row["seed"]), row["arm"], row["phase"]
        records.setdefault(key, []).append(row)
        for metric in ("acc_old", "acc_new", "acc_compatible"):
            assert 0 <= float(row[metric]) <= 1
        for metric in ("loss_old", "loss_new", "rate_next"):
            assert np.isfinite(float(row[metric])) and float(row[metric]) > 0
    expected_seeds = set(range(config["base_seed"], config["base_seed"] + config["n_seeds"]))
    assert {int(r["seed"]) for r in per_seed} == expected_seeds
    expected_count = config["n_seeds"] * (2 * (config["pre_steps"] // 10 + 1) + 7 * (config["post_steps"] // 10 + 1))
    assert len(curves) == expected_count
    assert len(per_seed) == 7 * config["n_seeds"]
    for (_, _, phase), rows in records.items():
        assert [int(r["step"]) for r in rows] == list(range(0, config["pre_steps" if phase == "pre" else "post_steps"] + 1, config["checkpoint_every"]))
    compatible = {int(r["seed"]): int(r["test_compatible"]) / int(r["test_examples"]) for r in manifest}
    for r in curves:
        q = compatible[int(r["seed"])]
        # On incompatible labels exactly one target is correct. On compatible
        # labels either both are correct or both are wrong.
        np.testing.assert_allclose(float(r["acc_old"]) + float(r["acc_new"]), 1 - q + 2 * q * float(r["acc_compatible"]), atol=1e-12)
    recomputed = {}
    for r in per_seed:
        seed, arm = int(r["seed"]), r["arm"]
        rs = records[(seed, arm, "post")]
        m = {}
        for metric in ("acc_old", "acc_new", "loss_new", "acc_compatible"):
            m[metric + "_start"] = float(rs[0][metric])
            m[metric + "_final"] = float(rs[-1][metric])
        m["new_gain_pp"] = 100 * (m["acc_new_final"] - m["acc_new_start"])
        m["old_change_pp"] = 100 * (m["acc_old_final"] - m["acc_old_start"])
        early = [p for p in rs if int(p["step"]) <= config["early_window"]]
        design = np.column_stack([np.ones(len(early)), [int(p["step"]) for p in early]])
        coef = np.linalg.lstsq(design, [float(p["acc_new"]) for p in early], rcond=None)[0]
        m["early_slope_pp_per_100"] = coef[1] * 10000
        values = [float(p["acc_new"]) for p in rs]
        m["mean_post_acc"] = sum((a + b) * config["checkpoint_every"] / 2 for a, b in zip(values, values[1:])) / config["post_steps"]
        hits = [i for i in range(len(rs) - config["threshold_consecutive"] + 1)
                if min(values[i:i + config["threshold_consecutive"]]) >= config["threshold"]]
        threshold = int(rs[hits[0]]["step"]) if hits else None
        assert (int(r["threshold_step"]) if r["threshold_step"] else None) == threshold
        for k, val in m.items():
            np.testing.assert_allclose(val, float(r[k]), rtol=1e-10, atol=1e-10)
        m["threshold_step"] = threshold
        recomputed[(seed, arm)] = m
    for arm, report in agg["arms"].items():
        rows = [recomputed[(s, arm)] for s in sorted(expected_seeds)]
        for metric, value in report.items():
            if metric == "recovery":
                hits = [r["threshold_step"] for r in rows if r["threshold_step"] is not None]
                assert value["n_reached"] == len(hits)
                assert value["median_among_reached"] == (float(np.median(hits)) if hits else None)
            else:
                data = [r[metric] for r in rows]
                np.testing.assert_allclose([value["mean"], value["sd"]], [np.mean(data), np.std(data, ddof=1)], atol=1e-10)
    for seed in expected_seeds:
        for arm in ("A_constant", "B_decay"):
            pre = records[(seed, arm, "pre")][-1]
            post = records[(seed, arm, "post")][0]
            for k in ("acc_old", "acc_new", "loss_old", "loss_new", "acc_compatible"):
                assert pre[k] == post[k]
        original = records[(seed, "B_decay", "post")][0]
        restored = records[(seed, "B_restored", "post")][0]
        for k in ("acc_old", "acc_new", "loss_old", "loss_new", "acc_compatible"):
            assert original[k] == restored[k]
    rng = np.random.default_rng(config["bootstrap_seed"])
    comparisons = [("constant_minus_decay_final_pp", "A_constant", "acc_new_final", 100),
                   ("constant_minus_decay_early_slope", "A_constant", "early_slope_pp_per_100", 1),
                   ("restored_minus_decay_final_pp", "B_restored", "acc_new_final", 100)]
    for label, arm, metric, factor in comparisons:
        paired = np.array([factor * (recomputed[(s, arm)][metric] - recomputed[(s, "B_decay")][metric]) for s in sorted(expected_seeds)])
        means = paired[rng.integers(0, len(paired), (config["bootstrap_resamples"], len(paired)))].mean(axis=1)
        np.testing.assert_allclose(agg["paired_bootstrap"][label]["ci95"], np.quantile(means, [.025, .975]), atol=1e-10)
        np.testing.assert_allclose(agg["paired_bootstrap"][label]["mean"], paired.mean(), atol=1e-10)
    rerun_files = []
    if args.rerun:
        (ROOT / ".work").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".work") as temp:
            subprocess.run([sys.executable, str(ROOT / "code/run_experiment.py"), "--output", temp], check=True, capture_output=True, text=True)
            for name in ("learning_curves.csv", "per_seed_metrics.csv", "dataset_manifest.csv", "summary.json"):
                assert sha(Path(temp) / name) == sha(ROOT / "analysis" / name), name
                rerun_files.append(name)
    with ZipFile(ROOT / "replication-lab.docx") as z:
        document = ET.fromstring(z.read("word/document.xml"))
        tables = []
        for tbl in document.findall(".//w:tbl", NS):
            table = []
            for tr in tbl.findall("w:tr", NS):
                table.append(["".join(t.text or "" for t in tc.findall(".//w:t", NS)) for tc in tr.findall("w:tc", NS)])
            tables.append(table)
        assert len(tables) == 2
        for idx, name in enumerate(("main-table.md", "control-table.md")):
            lines = (ROOT / "analysis" / name).read_text().splitlines()
            expected = [[v.strip() for v in line.strip("|").split("|")] for line in lines if line.startswith("|") and not line.startswith("|:--")]
            assert tables[idx] == expected, (name, tables[idx], expected)
        text = " ".join(t.text or "" for t in document.findall(".//w:t", NS))
        for token in ("Suryansh Soni", "September 27, 2026", "Partially Reproduced", "37.35", "37.06", "37.63", "49.98", "12.59", "51.00", "50.32", "51.67", "37.34", "37.62", "99.86", "99.87", "99.88", "0.489", "0.128"):
            assert token in text, token
        for token in ("[Insert", "[Write", "Student Name", "[?]", "\u2014"):
            assert token not in text, token
        media_hashes = {hashlib.sha256(z.read(name)).hexdigest() for name in z.namelist() if name.startswith("word/media/")}
        for name in ("learning_and_retention.png", "adaptation_controls.png"):
            assert sha(ROOT / "figures" / name) in media_hashes
    result = {"status": "PASS", "checkpoint_rows": len(curves), "per_seed_rows": len(per_seed),
              "checks": ["gradient versus finite differences", "complete checkpoint grids and finite metrics",
                         "independent per-seed slopes and recovery", "summary means and standard deviations",
                         "paired bootstrap intervals", "same weights at task switch and restoration baseline",
                         "compatible-label accuracy identity", "rendered DOCX tables match generated evidence",
                         "key narrative values, author, date, and verdict present", "embedded figure hashes match"],
              "gradient_max_absolute_error": check_gradient(),
              "byte_identical_rerun_files": rerun_files,
              "report_sha256": sha(ROOT / "replication-lab.docx"),
              "evidence_sha256": {name: sha(ROOT / "analysis" / name) for name in ("learning_curves.csv", "per_seed_metrics.csv", "summary.json")}}
    (ROOT / "analysis/reproduction_check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
