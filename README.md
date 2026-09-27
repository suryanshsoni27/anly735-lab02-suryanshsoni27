# ANLY 735 Week 4 Replication Laboratory 2

**Can the Model Keep Learning?**

Suryansh Soni | September 27, 2026

This repository contains the Word report, Quarto source, and reproducibility
record for a supervised proxy experiment on learning after a target change.
The anchor is Klein et al. (2024), *Plasticity Loss in Deep Reinforcement
Learning: A Survey*, [arXiv version 1](https://arxiv.org/abs/2411.04832v1).

**Verdict: Partially Reproduced.** Two learners with similarly strong initial
performance adapt at different speeds, but restoring the slower learner's
learning rate removes its deficit. This supports a narrow behavioral claim;
it does not establish intrinsic neural-network plasticity loss.

## Deliverables

- [Final Word report](replication-lab.docx), the Canvas deliverable.
- [Quarto source](replication-lab.qmd), including the complete diagnostic.
- [Numerical summary](analysis/summary.json) and [verification record](analysis/reproduction_check.json).
- [Main experiment](code/run_experiment.py) and [fixed design](provenance/design.md).

## Course template provenance and workflow exception

The assignment links to
[the general course scaffold](https://github.com/ANLY-735-Predictive-AI/anly735-templates/tree/main/replication-lab).
At source commit `2326687d77e54ddc30ae34367e48cec1a6069027`, the linked directory
contained only a README, `replication-lab.qmd`, and a bibliography placeholder.
No executable Lab 2 experiment was present, and the parent repository's
`is_template` flag was false. The same link was confirmed on the Canvas Lab 2
assignment. The public course organization did not list a separate Lab 2
starter at the time of inspection.

This repository was therefore created independently under the student's
account and cloned before analysis. The report scaffold was adapted locally;
the course repository was never modified. This is **not** a GitHub-generated
copy of an enabled template and **not** a run of instructor-supplied code.
The unchanged scaffold and README are retained in `provenance/`, with source
status and version information. The original CC BY 4.0 attribution is preserved
in `LICENSE`. A separate starter, if provided later, would require its own run.

The design and main implementation were committed before execution in commit
`5bb37cb5b70b833f240c2c14faf6164a7e8ac8d9`. No hyperparameter search was performed.
Later work generated evidence, wrote the report, added independent verification,
and adjusted figure/document layout.

## Experiment

For each of 30 independent seeds, generate two independent N(0,1) predictors.
Task A predicts the sign of x1; Task B predicts the sign of x2. Two logistic
regressions start at zero and receive 600 batches on A and 400 batches on B,
with 64 examples per batch. A separate random stream generates 4,096 test
observations. Training and evaluation observations are never mixed. All agents
share the same batches and evaluation inputs within a seed.

| Condition | Starting weights at the change | Future learning rate |
|---|---|---|
| A constant rate | A pretrained weights | 0.2 |
| B decreasing rate | B pretrained weights | 0.2 / (1 + t/20) |
| B rate restored | Exact copy of B | 0.2 |
| Fresh constant rate | Zero | 0.2 |
| Fresh aged schedule | Zero | 0.2 / (1 + t/20) |
| A stationary | Exact copy of A; remains on A | 0.2 |
| B stationary | Exact copy of B; remains on A | 0.2 / (1 + t/20) |

Here t is the cumulative zero-based update index, including the 600 previous
updates. L2 coefficient 0.0001 applies to feature weights, not the intercept.
There is no replay, early stopping, or test-based model selection. Settings are
in `config.json`; seeds are 20260927 through 20260956. The bootstrap seed is
73502 and 10,000 paired seed resamples are used.

## Metrics

- New-task accuracy and cross-entropy assess adaptation after the rule changes.
- Full old-task accuracy assesses retention of the old rule.
- Compatible accuracy uses only test inputs with matching labels under both
  rules, isolating behavior still useful under the new task.
- Early slope is OLS accuracy slope across checkpoints 0, 10, ..., 50,
  expressed in percentage points per 100 updates. It is not an extrapolation.
- Recovery is the first 90% checkpoint confirmed at the next two checkpoints.
  The last confirmable starting checkpoint is update 380. An unreached
  threshold is empty in CSV, null in JSON, and `>400` in the report. In these
  runs every unrecovered model was also below 90% at update 400. Success counts
  keep censoring distinct from observed recovery.
- Mean trajectory accuracy is trapezoidal area under the new-task accuracy
  curve, divided by the 400-update window.
- Inferential intervals bootstrap paired seed differences. Figure bands are
  pointwise means plus/minus 1.96 standard errors, not simultaneous bands.

Stationary controls are evaluated on both rules for consistent storage, but
their appropriate success measure is **old-task accuracy**. Their new-task
recovery entries do not mean the stationary experiment failed.

## Main findings

Both main agents average 99.80% initial accuracy. At the target change, their
new-task accuracy is near chance. After 400 additional updates:

| Condition | New accuracy | Old accuracy | Median updates to 90% |
|---|---:|---:|---:|
| A constant rate | 99.81% | 49.94% | 90; 30/30 runs |
| B decreasing rate | 62.46% | 87.40% | Not reached; 0/30 |
| B rate restored | 99.80% | 49.92% | 45; 30/30 runs |
| Fresh constant rate | 99.80% | 49.92% | 10; 30/30 runs |
| Fresh aged schedule | 99.75% | 49.89% | 10; 30/30 runs |

The A-minus-B new-task accuracy gap is 37.35 percentage points (paired 95%
bootstrap interval 37.06 to 37.63). Restoring B's rate raises final accuracy by
37.34 points (37.06 to 37.62). See `analysis/summary.json` for unrounded results
and standard deviations.

The target rules conflict on about half the inputs, so one prediction cannot
satisfy both there. A's lower old-task accuracy should not be misreported as
loss of useful knowledge: both agents retain almost all compatible labels.
B improves substantially and should not be described as having stopped learning.

## Reproduce

Tested: Python 3.13.11, NumPy 2.5.3, Matplotlib 3.11.2, Quarto 1.10.18,
macOS 26.5 arm64. The full analysis environment is pinned in `requirements.txt`.
No external dataset or GPU is needed.

```bash
git clone https://github.com/suryanshsoni27/anly735-lab02-suryanshsoni27.git
cd anly735-lab02-suryanshsoni27
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python code/run_experiment.py
python code/make_figures.py
python code/make_tables.py
python code/render_report.py
python code/verify_results.py --rerun
```

Install the official [Quarto CLI](https://quarto.org/docs/get-started/) and put
`quarto` on PATH, or pass `--quarto /absolute/path/to/quarto` to `render_report.py`.
That script calls `quarto render replication-lab.qmd --to docx` and then fixes
Word table widths and figure pagination using standard-library XML tools. It
does not change text or results. The committed `reference.docx` supplies the
academic style settings. Its optional regeneration script, `make_reference.py`,
requires python-docx; regeneration is not needed for the commands above.

The verifier reruns the full experiment in a temporary folder, checks
byte-identical numerical outputs, independently recalculates metrics from the
checkpoint CSV, checks the logistic gradient against finite differences, and
compares Word tables and embedded figure hashes with the generated evidence.
The Word report was also rendered to page images for visual inspection. Those
temporary QA files are excluded from Git.

## Repository map

```text
replication-lab.qmd / .docx       Source and Canvas report
references.bib                  Bibliographic metadata
reference.docx                  Word style reference
config.json                     Settings fixed before execution
requirements.txt                Exact analysis dependencies
code/run_experiment.py           Data generation, learning, metrics
code/make_figures.py             Figures from saved checkpoints
code/make_tables.py              Tables from saved summaries
code/render_report.py            Official Quarto render and Word layout
code/verify_results.py           Evidence and report checks
analysis/learning_curves.csv     12,270 checkpoint records
analysis/per_seed_metrics.csv    210 seed-condition summaries
analysis/dataset_manifest.csv    Sizes, class counts, input fingerprints
analysis/summary.json            Means, SDs, recovery, paired intervals
analysis/environment.json        Runtime and source fingerprints
analysis/reproduction_check.json Verification and report fingerprint
analysis/visual_review.json      Rendered-document QA record
figures/                        Two report figures
provenance/                     Course scaffold and source/design record
data/README.md                  Synthetic-data regeneration
```

## Scope and transparency

This is a single-change, linear, noiseless, supervised proxy. There are no
hidden neurons or reinforcement-learning dynamics. Rate restoration supports
a causal statement about that intervention from the same B checkpoint; the
overall A/B comparison also includes different pretraining weights. The study
does not establish representation collapse, permanent plasticity loss, or
performance across real-world tasks.

Codex assisted with code, report preparation, and execution of verification.
All numerical findings are traceable to saved checkpoints. The report discloses
AI assistance and the unavailable course starter/template-generation path.
