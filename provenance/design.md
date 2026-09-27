# Experiment design fixed before the main run

The linked course repository supplies a report scaffold, not executable Lab 2
code. This is a newly implemented supervised proxy experiment, not recovered
instructor code and not a deep reinforcement learning replication.

The feature distribution stays N(0, I) in two dimensions. Task A is the sign of
x1; Task B is the sign of x2. After 600 mini-batch updates the target switches
from A to B. Every comparison uses the same training batches and held-out
examples within each seed. The test set never supplies a gradient.

Primary comparison: logistic regression with a constant learning rate of 0.2
(Agent A) versus a decreasing rate 0.2 / (1 + update_index / 20) (Agent B).
The update index is zero based and is not reset at the task boundary. Both
learners start at zero and receive the same L2 penalty and data. Different
pretraining weights are a consequence of their learning schedules.

Controls at the change:

- Clone Agent B and restore a constant rate of 0.2. The starting weights and
  all future batches match B exactly; only the rate differs.
- Fresh zero weights with a constant rate of 0.2.
- Fresh zero weights with B's accumulated, decreasing learning rate.
- Continue each original agent on Task A without a change, on the same input
  batches, to separate nonstationarity from ordinary training drift.

Evaluate immediately before any B updates, then every 10 updates for 400
updates. Report new-task accuracy and cross-entropy, old-task accuracy,
accuracy on the subset whose labels agree, early accuracy slope over updates
0 through 50, and first 90% checkpoint confirmed by two further checkpoints.
Never encode failure to reach the threshold as a recovery time of 400.
Summarize 30 independent seeds; bootstrap paired seed differences for the
primary final accuracy, early slope, and rate-restoration comparisons.

No hyperparameter search or result-dependent stopping is used. This is a
controlled learning-schedule intervention. A slow trajectory alone cannot
establish dead neurons, representational collapse, or intrinsic plasticity loss.
Old and new targets disagree on about half the input space, so total old-task
accuracy can decrease even when all compatible knowledge is retained.

The design is committed before running the experiment. Any later analytical
change must be described in the Git history and results documentation.
