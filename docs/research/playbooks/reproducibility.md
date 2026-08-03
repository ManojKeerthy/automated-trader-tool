# PLAYBOOK: REPRODUCIBILITY

To reproduce any past experiment:
1. Fetch `ExperimentRecord` by `experiment_id`.
2. Inspect environment metadata (Python version, package versions, execution hash).
3. Load frozen dataset version and universe membership.
4. Execute code using identical random seed.
