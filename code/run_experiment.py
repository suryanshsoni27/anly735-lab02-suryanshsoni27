"""Deterministic, paired proxy for adaptation under a changing target rule."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("A_constant", "B_decay", "B_restored", "fresh_constant", "fresh_aged")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def update(w, x, y, rate, l2):
    z = x @ w
    p = 1 / (1 + np.exp(-np.clip(z, -700, 700)))
    penalty = l2 * w.copy()
    penalty[-1] = 0.0  # no penalty on the intercept
    return w - rate * (x.T @ (p - y) / len(y) + penalty)


def evaluate(w, x, ya, yb):
    z = x @ w
    pred = z >= 0
    agree = ya == yb
    return {
        "acc_old": float(np.mean(pred == ya)),
        "acc_new": float(np.mean(pred == yb)),
        "loss_old": float(np.mean(np.logaddexp(0, z) - ya * z)),
        "loss_new": float(np.mean(np.logaddexp(0, z) - yb * z)),
        "acc_compatible": float(np.mean(pred[agree] == ya[agree])),
    }


def write_csv(path, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def first_sustained(rows, threshold, consecutive):
    for i in range(len(rows) - consecutive + 1):
        if all(r["acc_new"] >= threshold for r in rows[i:i + consecutive]):
            return rows[i]["step"]
    return None


def seed_summary(rows, config):
    first, last = rows[0], rows[-1]
    early = [r for r in rows if r["step"] <= config["early_window"]]
    t = np.array([r["step"] for r in early], dtype=float)
    a = np.array([r["acc_new"] for r in early])
    slope = float(np.sum((t - t.mean()) * (a - a.mean())) / np.sum((t - t.mean()) ** 2))
    out = {"seed": first["seed"], "arm": first["arm"]}
    for key in ("acc_old", "acc_new", "loss_new", "acc_compatible"):
        out[key + "_start"] = first[key]
        out[key + "_final"] = last[key]
    out["new_gain_pp"] = 100 * (last["acc_new"] - first["acc_new"])
    out["old_change_pp"] = 100 * (last["acc_old"] - first["acc_old"])
    out["early_slope_pp_per_100"] = slope * 100 * 100
    out["mean_post_acc"] = float(np.trapezoid([r["acc_new"] for r in rows], [r["step"] for r in rows]) / config["post_steps"])
    out["threshold_step"] = first_sustained(rows, config["threshold"], config["threshold_consecutive"])
    return out


def run(config):
    curves, summary, datasets = [], [], []
    eta = config["learning_rate"]
    every = config["checkpoint_every"]
    decay = lambda t: eta / (1 + t / config["decay_scale"])
    for seed in range(config["base_seed"], config["base_seed"] + config["n_seeds"]):
        rng_train, rng_test = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(2)]
        # Draw all inputs before fitting; test and training use independent RNGs.
        total = config["pre_steps"] + config["post_steps"]
        raw = rng_train.normal(size=(total, config["batch_size"], 2))
        train = np.concatenate([raw, np.ones((*raw.shape[:2], 1))], axis=2)
        raw_test = rng_test.normal(size=(config["test_size"], 2))
        test = np.column_stack([raw_test, np.ones(config["test_size"])])
        ya, yb = test[:, 0] >= 0, test[:, 1] >= 0
        datasets.append({"seed": seed, "training_examples": int(total * config["batch_size"]),
                         "test_examples": len(test), "test_positive_a": int(ya.sum()),
                         "test_positive_b": int(yb.sum()), "test_compatible": int((ya == yb).sum()),
                         "train_sha256": hashlib.sha256(train.tobytes()).hexdigest(),
                         "test_sha256": hashlib.sha256(test.tobytes()).hexdigest()})
        weights = {"A_constant": np.zeros(3), "B_decay": np.zeros(3)}
        for step in range(config["pre_steps"] + 1):
            if step % every == 0:
                for arm, w in weights.items():
                    curves.append({"seed": seed, "phase": "pre", "arm": arm,
                                   "step": step, "global_step": step, "rate_next": eta if arm == "A_constant" else decay(step),
                                   **evaluate(w, test, ya, yb)})
            if step == config["pre_steps"]:
                break
            x = train[step]
            for arm in weights:
                rate = eta if arm == "A_constant" else decay(step)
                weights[arm] = update(weights[arm], x, x[:, 0] >= 0, rate, config["l2"])
        weights.update({"B_restored": weights["B_decay"].copy(), "fresh_constant": np.zeros(3),
                        "fresh_aged": np.zeros(3), "A_stationary": weights["A_constant"].copy(),
                        "B_stationary": weights["B_decay"].copy()})
        post = {arm: [] for arm in weights}
        for step in range(config["post_steps"] + 1):
            g = config["pre_steps"] + step
            if step % every == 0:
                for arm, w in weights.items():
                    row = {"seed": seed, "phase": "post", "arm": arm, "step": step,
                           "global_step": g, "rate_next": decay(g) if arm in ("B_decay", "fresh_aged", "B_stationary") else eta,
                           **evaluate(w, test, ya, yb)}
                    post[arm].append(row)
                    curves.append(row)
            if step == config["post_steps"]:
                break
            x = train[g]
            for arm in weights:
                rate = decay(g) if arm in ("B_decay", "fresh_aged", "B_stationary") else eta
                y = x[:, 0] >= 0 if arm.endswith("stationary") else x[:, 1] >= 0
                weights[arm] = update(weights[arm], x, y, rate, config["l2"])
        summary.extend(seed_summary(post[arm], config) for arm in weights)
    return curves, summary, datasets


def aggregate(rows, config):
    out = {"config": config, "arms": {}, "paired_bootstrap": {}}
    metrics = [k for k in rows[0] if k not in ("seed", "arm", "threshold_step")]
    for arm in sorted(set(r["arm"] for r in rows)):
        group = [r for r in rows if r["arm"] == arm]
        out["arms"][arm] = {key: {"mean": float(np.mean([r[key] for r in group])),
                                  "sd": float(np.std([r[key] for r in group], ddof=1))} for key in metrics}
        reached = [r["threshold_step"] for r in group if r["threshold_step"] is not None]
        out["arms"][arm]["recovery"] = {"n_reached": len(reached), "n_total": len(group),
                                         "median_among_reached": float(np.median(reached)) if reached else None,
                                         "min": min(reached) if reached else None, "max": max(reached) if reached else None}
    rng = np.random.default_rng(config["bootstrap_seed"])
    for label, first, second, metric, factor in [
        ("constant_minus_decay_final_pp", "A_constant", "B_decay", "acc_new_final", 100),
        ("constant_minus_decay_early_slope", "A_constant", "B_decay", "early_slope_pp_per_100", 1),
        ("restored_minus_decay_final_pp", "B_restored", "B_decay", "acc_new_final", 100),
    ]:
        a = {r["seed"]: r[metric] for r in rows if r["arm"] == first}
        b = {r["seed"]: r[metric] for r in rows if r["arm"] == second}
        d = factor * np.array([a[s] - b[s] for s in sorted(a)])
        boot = d[rng.integers(0, len(d), size=(config["bootstrap_resamples"], len(d)))].mean(axis=1)
        out["paired_bootstrap"][label] = {"mean": float(d.mean()), "ci95": np.quantile(boot, [0.025, 0.975]).tolist()}
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "analysis")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    config = json.loads((ROOT / "config.json").read_text())
    curves, summary, datasets = run(config)
    write_csv(args.output / "learning_curves.csv", curves)
    write_csv(args.output / "per_seed_metrics.csv", summary)
    write_csv(args.output / "dataset_manifest.csv", datasets)
    agg = aggregate(summary, config)
    (args.output / "summary.json").write_text(json.dumps(agg, indent=2) + "\n")
    env = {"python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform(),
           "config_sha256": digest(ROOT / "config.json"), "analysis_code_sha256": digest(__file__),
           "rows": len(curves), "seeds": config["n_seeds"], "pretraining_step_range": [0, config["pre_steps"]],
           "post_step_range": [0, config["post_steps"]]}
    (args.output / "environment.json").write_text(json.dumps(env, indent=2) + "\n")
    print(json.dumps({arm: {"new_final": v["acc_new_final"]["mean"],
                                "old_final": v["acc_old_final"]["mean"],
                                "early_slope": v["early_slope_pp_per_100"]["mean"],
                                "recovery": v["recovery"]} for arm, v in agg["arms"].items()}, indent=2))


if __name__ == "__main__":
    main()
