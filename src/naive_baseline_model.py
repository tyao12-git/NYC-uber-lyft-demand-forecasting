import pandas as pd
import numpy as np

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor


# =========================================================
# 1. Load data
# =========================================================

df = pd.read_csv("/Users/tommyyao/Desktop/Uber Project/demand_features.csv")

# request hour transformation
df["request_hour"] = pd.to_datetime(df["request_hour"])
df = df.sort_values(
    ["request_hour", "pickup_zone", "company"]
).reset_index(drop=True)

# time ordering sequence
df = df.sort_values("request_hour").reset_index(drop=True)


# =========================================================
# 2. Basic cleaning
# =========================================================


df = df.dropna(
    subset=[
        "demand",
        "lag_1h",
        "lag_24h",
        "lag_168h"
    ]
)


# =========================================================
# 3. Time features
# =========================================================

df["hour"] = df["request_hour"].dt.hour
df["day_of_week"] = df["request_hour"].dt.dayofweek
df["month"] = df["request_hour"].dt.month
df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
df["is_snowing"] = df["is_snowing"].map({
    "Yes": 1,
    "No": 0
})


# =========================================================
# 4. Define predictors
# =========================================================

features = [
    # time
    "hour_of_day",
    "day_of_week",
    "month",
    "is_weekend",

    # demand history
    "lag_1h",
    "lag_2h",
    "lag_24h",
    "lag_168h",

    # rolling demand
    "rolling_3h_avg",
    "rolling_6h_avg",
    "rolling_24h_avg",

    # weather
    "temp",
    "is_snowing",
    "wind_category",
    "rain_category",

    # categorical
    "pickup_zone",
    "company"
]

target = "demand"


# =========================================================
# 5. One-hot encoding
# =========================================================

X = df[features]
y = df[target]

X = pd.get_dummies(
    X,
    columns=["pickup_zone", "company", "wind_category", "rain_category"],
    drop_first=False
)


# =========================================================
# 6. Time-based train/test split
# =========================================================

train_end=pd.Timestamp("2025-11-01")

train_mask = df["request_hour"] < train_end
test_mask = df["request_hour"] >= train_end


X_train = X.loc[train_mask]
X_test = X.loc[test_mask]

y_train = y.loc[train_mask]
y_test = y.loc[test_mask]


print("Train size:", len(X_train))
print("Test size:", len(X_test))


# =========================================================
# 7. Naive baseline
# =========================================================

daily_naive_pred = df.loc[test_mask,"lag_24h"]

naive_mae = mean_absolute_error(y_test, daily_naive_pred)
naive_rmse = np.sqrt(mean_squared_error(y_test, daily_naive_pred))

print("\nNaive Baseline")
print("MAE:", naive_mae)
print("RMSE:", naive_rmse)


# =========================================================
# 8. XGBoost baseline
# =========================================================

model = XGBRegressor(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    tree_method="hist",
    n_jobs=-1,
    random_state=42
)

model.fit(X_train, y_train)


# =========================================================
# 9. Prediction
# =========================================================

y_pred = model.predict(X_test)

# =========================================================
# 9.1 Prediction Results
# =========================================================
results = df.loc[test_mask, [
    "request_hour",
    "pickup_zone",
    "company",
    "demand"
]].copy()

results["predicted_demand"] = y_pred

results["residual"] = (
    results["demand"] - results["predicted_demand"]
)

print("\nPrediction Sample:")
print(results.head(20))

# =========================================================
# 10. Evaluation
# =========================================================

mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\nXGBoost Baseline")
print("MAE:", mae)
print("RMSE:", rmse)
print("R²:", r2)

print("Data loaded")
print(df.shape)

print("Encoding finished")
print(X.shape)

print("Starting training...")

model.fit(X_train, y_train)

print("Training finished")

print(df.columns.tolist())
print("baseline model completed")
# ==============saved result and model==============



from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR = PROJECT_ROOT / "outputs"
MODEL_DIR = PROJECT_ROOT / "models"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)



results.to_csv(
    OUTPUT_DIR / "xgboost_predictions_baseline.csv",
    index=False
)

model.save_model(
    MODEL_DIR / "xgboost_baseline.json"
)
# ==================================================

