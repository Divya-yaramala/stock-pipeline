# ADR 058 - AutoML Pipeline Pattern

## Status
Accepted

## Context
Manually choosing ML models is time-consuming and subjective. Engineers must evaluate multiple algorithm families, tune hyperparameters by hand, and risk selecting a suboptimal model based on familiarity rather than empirical performance.

## Decision
Built an AutoML pipeline that automatically trains and compares 5 candidate models, selects the winner by lowest RMSE, and supports GridSearchCV-based hyperparameter tuning for the winning model family.

## Reasons
- 5 models cover linear, tree, and boosting paradigms — no single family dominates all datasets
- Winner selected objectively by lowest RMSE, removing subjectivity from model selection
- Hyperparameter tuning with GridSearchCV for fine-tuning the best model class
- Cross-validation prevents overfitting bias by evaluating on held-out folds
- Results saved to S3 for reproducibility and audit trail

## Consequences
- AutoML takes longer than single model training (5× the compute per run)
- GridSearchCV can be slow — 27 combinations for Random Forest (3×3×3)
- All runs are reproducible and comparable via S3-stored result JSON
- Future: add Bayesian optimization (e.g., Optuna) for faster tuning with fewer evaluations
