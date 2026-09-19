import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

results = pd.read_csv(
    PROJECT_ROOT / "outputs" / "xgboost_predictions_baseline.csv"
)

print("\nResidual Summary:")
print(results["residual"].describe())


results["abs_error"] = results["residual"].abs()
print("absolute error summary:")
print(results["abs_error"].describe())

print("demand prediction error of baseline model by demand level:")
bins = [0, 10, 50, 100, 200, 500, float("inf")]

results["demand_level"] = pd.cut(
    results["demand"],
    bins=bins
)

error_by_level = (
    results
    .groupby("demand_level", observed=True)
    .agg(
        observations=("demand", "size"),
        avg_demand=("demand", "mean"),
        avg_predicted_demand=("predicted_demand", "mean"),
        avg_residual=("residual", "mean"),
        mae=("abs_error", "mean"),
        total_demand=("demand", "sum"),
        total_abs_error=("abs_error", "sum")
    )
)

error_by_level["normalized_mae"] = (
    error_by_level["total_abs_error"]
    / error_by_level["total_demand"]
)

print(error_by_level)