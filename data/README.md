# Synthetic data

No external or private data are used. `code/run_experiment.py` generates inputs
locally from the seeds in `config.json`. Each seed spawns separate training and
test random streams with NumPy SeedSequence. Inputs have two independent
standard-normal features; a column of ones supplies the intercept. Task A is
`x1 >= 0`; Task B is `x2 >= 0`.

Each run has 64,000 training examples and 4,096 held-out inputs. The file
`analysis/dataset_manifest.csv` records class counts, compatible-label counts,
and SHA-256 fingerprints of the actual arrays. Storing every raw array is
unnecessary because the generator, seeds, versions, and hashes are provided.
Repeated evaluation measures learning trajectories, never parameter selection.
