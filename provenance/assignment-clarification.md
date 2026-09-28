# Clarified laboratory scope

Source: Dr. Itauma's Lab 2 clarification, supplied by the student on
September 27, 2026. The announcement's original posting date and URL were not
supplied. This note summarizes the relevant requirements.

- Klein et al. is a survey of prior studies, not a primary empirical study
  with one original learning experiment to reproduce.
- Construct a controlled learning experiment from scratch that introduces
  nonstationarity and produces a post-change learning trajectory.
- Apply Change, Retention, New Learning, Rate, and Tradeoff to that evidence.
- A conceptual figure or deterministic formula can support the analysis but
  cannot replace a learning experiment.
- Limit the verdict to the investigated phenomenon. Use Reproduced,
  Partially Reproduced, Not Reproduced, or Inconclusive.
- Diagnose learning behavior after the change rather than inferring plasticity
  loss from the immediate performance drop.

The existing experiment satisfies this scope: it trains logistic models from
scratch, changes the target rule, records learning and retention trajectories,
and compares matched controls across 30 seeds. The clarification changes the
description of the assignment scope, not the experiment, configuration, or
numerical results. The report and README now describe the experiment as the
assigned proxy approach. The separate GitHub template-setting limitation
remains documented in the repository provenance.
