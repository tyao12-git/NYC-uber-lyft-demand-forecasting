# ============================================================
# FINAL MODEL - NYC Uber/Lyft Hourly Demand Forecasting
# XGBoost
# ============================================================

import pandas as pd
import numpy as np
import xgboost as xgb

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

import holidays


# ============================================================
# 1. LOAD DATA
# ============================================================

df = pd.read_csv("demand_features.csv")

df["request_hour"] = pd.to_datetime(df["request_hour"])

# Always sort time-series data before creating lag/rolling features
df = df.sort_values(
    ["pickup_zone", "company", "request_hour"]
).reset_index(drop=True)

print("Dataset shape:", df.shape)
print(df.head())


# ============================================================
# 2. BASIC TIME FEATURES
# ============================================================

df["hour"] = df["request_hour"].dt.hour
df["day_of_week"] = df["request_hour"].dt.dayofweek
df["month"] = df["request_hour"].dt.month

df["is_weekend"] = (
    df["day_of_week"] >= 5
).astype(int)


# ============================================================
# 3. HOLIDAY FEATURES
# ============================================================

us_holidays = holidays.US(years=[2025])

df["date"] = df["request_hour"].dt.date

df["is_holiday"] = df["date"].apply(
    lambda x: int(x in us_holidays)
)


# Optional:
# Keep this for analysis even 
df["holiday_name"] = df["date"].apply(
    lambda x: us_holidays.get(x, "Non-Holiday")
)


# ============================================================
# 4. ZONE × HOUR INTERACTION
# ============================================================

df["zone_hour"] = (
    df["pickup_zone"].astype(str)
    + "_H"
    + df["hour"].astype(str)
)


# ============================================================
# 5. LAG FEATURES
# ============================================================
# IMPORTANT:
# Group by pickup_zone + company so that lag demand comes
# from the SAME demand series.

group_cols = ["pickup_zone", "company"]

df["lag_1h"] = (
    df.groupby(group_cols)["demand"]
      .shift(1)
)

df["lag_24h"] = (
    df.groupby(group_cols)["demand"]
      .shift(24)
)

df["lag_168h"] = (
    df.groupby(group_cols)["demand"]
      .shift(168)
)


# ============================================================
# 6. ROLLING FEATURES
# ============================================================
# shift(1) is CRITICAL:
# Current demand must NOT enter its own predictor.

df["rolling_mean_3h"] = (
    df.groupby(group_cols)["demand"]
      .transform(
          lambda x: x.shift(1).rolling(3).mean()
      )
)

df["rolling_mean_24h"] = (
    df.groupby(group_cols)["demand"]
      .transform(
          lambda x: x.shift(1).rolling(24).mean()
      )
)

df["rolling_mean_168h"] = (
    df.groupby(group_cols)["demand"]
      .transform(
          lambda x: x.shift(1).rolling(168).mean()
      )
)


# ============================================================
# 7. OPTIONAL: ROLLING MAX
# Useful for detecting recent demand spikes
# ============================================================

df["rolling_max_24h"] = (
    df.groupby(group_cols)["demand"]
      .transform(
          lambda x: x.shift(1).rolling(24).max()
      )
)


# ============================================================
# 8. REMOVE ROWS WITHOUT ENOUGH HISTORY
# ============================================================

required_history = [
    "lag_1h",
    "lag_24h",
    "lag_168h",
    "rolling_mean_3h",
    "rolling_mean_24h",
    "rolling_mean_168h"
]

df = df.dropna(subset=required_history).copy()

print("After lag/rolling NA removal:", df.shape)


# ============================================================
# 9. CATEGORICAL VARIABLES
# ============================================================

categorical_cols = [
    "pickup_zone",
    "company",
    "zone_hour"
]

# Add these only if they exist in your dataset
optional_categorical = [
    "rain_category",
    "wind_category"
]

for col in optional_categorical:
    if col in df.columns:
        categorical_cols.append(col)

for col in categorical_cols:
    df[col] = df[col].astype("category")


# ============================================================
# 10. FINAL FEATURES
# ============================================================

features = [

    # Temporal
    "hour",
    "day_of_week",
    "month",
    "is_weekend",

    # Calendar
    "is_holiday",

    # Spatial / company
    "pickup_zone",
    "company",

    # Spatial × Temporal interaction
    "zone_hour",

    # Demand history
    "lag_1h",
    "lag_24h",
    "lag_168h",

    # Rolling demand
    "rolling_mean_3h",
    "rolling_mean_24h",
    "rolling_mean_168h",
    "rolling_max_24h",

]





# ============================================================
# 11. ADD WEATHER FEATURES IF AVAILABLE
# ============================================================
df["is_snowing"] = (
    df["is_snowing"]
    .map({
        "Yes": 1,
        "No": 0
    })
    .astype("int8")
)

weather_features = [
    "temp",
    "rain_category",
    "wind_category",
    "is_snowing"
]

for col in weather_features:
    if col in df.columns:
        features.append(col)


target = "demand"

print("\nFinal predictors:")
for feature in features:
    print("-", feature)


# ============================================================
# 12. TIME-BASED TRAIN / VALIDATION / TEST SPLIT
# ============================================================
# MODIFY THESE DATES based on your actual dataset.
#
# Example:
# Jan-Aug  -> Training
# Sep-Oct  -> Validation
# Nov-Dec  -> Test
#
# DO NOT use train_test_split(random_state=...)
# for this forecasting problem.

train_end = "2025-08-31 23:59:59"
valid_end = "2025-10-31 23:59:59"

train = df[
    df["request_hour"] <= train_end
].copy()

valid = df[
    (df["request_hour"] > train_end)
    & (df["request_hour"] <= valid_end)
].copy()

test = df[
    df["request_hour"] > valid_end
].copy()


X_train = train[features]
y_train = train[target]

X_valid = valid[features]
y_valid = valid[target]

X_test = test[features]
y_test = test[target]



# ============================================================
# 13. FINAL XGBOOST MODEL
# ============================================================

model = xgb.XGBRegressor(

    objective="reg:squarederror",

    n_estimators=1000,

    learning_rate=0.03,

    max_depth=7,

    min_child_weight=5,

    subsample=0.8,

    colsample_bytree=0.8,

    reg_alpha=0.1,

    reg_lambda=1.0,

    random_state=42,

    tree_method="hist",

    enable_categorical=True,

    eval_metric="mae"
)


# ============================================================
# 14. TRAIN MODEL
# ============================================================
# ============================================================
# SAMPLE WEIGHTS FOR HIGH-DEMAND OBSERVATIONS
# ============================================================

weights = np.ones(len(y_train), dtype=float)
weights[
    (y_train > 0) &
    (y_train < 50)
] = 2.0
weights[
    (y_train >= 50) &
    (y_train < 500)
] = 1.25

weights[
    y_train >= 500
] = 5

model.fit(
    X_train,
    y_train,
    sample_weight=weights,

    eval_set=[
        (X_train, y_train),
        (X_valid, y_valid)
    ],

    verbose=50
)
# ============================================================
# 14A. CREATE HIGH-DEMAND RESIDUAL CORRECTION DATA
# ============================================================
# The main model has already been trained on the training set.
# We now use validation predictions to construct residuals.
# This avoids training the correction model on in-sample
# residuals from the main training set.

# Main-model predictions on validation data
valid["main_prediction"] = model.predict(X_valid)

# Residual = actual demand - main model prediction
valid["correction_target"] = (
    valid["demand"]
    - valid["main_prediction"]
)

# Focus the correction model on high-demand observations
# 350 is the initial threshold for defining the high-demand regime.
high_valid = valid[
    valid["demand"] >= 450
].copy()

print("\n==============================")
print("HIGH-DEMAND CORRECTION DATA")
print("==============================")

print(
    "High-demand validation observations:",
    len(high_valid)
)

print(
    "Average correction target:",
    high_valid["correction_target"].mean()
)

print(
    "Average actual demand:",
    high_valid["demand"].mean()
)

print(
    "Average main prediction:",
    high_valid["main_prediction"].mean()
)


# ============================================================
# 14B. TRAIN HIGH-DEMAND RESIDUAL CORRECTION MODEL
# ============================================================

# Use all original predictors plus the main model's prediction.
correction_features = features + [
    "main_prediction"
]

X_correction = high_valid[
    correction_features
]

y_correction = high_valid[
    "correction_target"
]


correction_model = xgb.XGBRegressor(

    objective="reg:squarederror",

    n_estimators=400,

    learning_rate=0.03,

    max_depth=4,

    min_child_weight=10,

    subsample=0.8,

    colsample_bytree=0.8,

    reg_alpha=0.1,

    reg_lambda=1.0,

    random_state=42,

    tree_method="hist",

    enable_categorical=True
)


correction_model.fit(
    X_correction,
    y_correction,
    verbose=False
)

print("\nHigh-demand correction model trained.")


# ============================================================
# 15. TEST PREDICTION
# ============================================================

test["predicted_demand"] = model.predict(X_test)

# Demand cannot be negative
test["predicted_demand"] = np.maximum(
    test["predicted_demand"],
    0
)


# ============================================================
# 16. OVERALL METRICS
# ============================================================

mae = mean_absolute_error(
    y_test,
    test["predicted_demand"]
)

rmse = np.sqrt(
    mean_squared_error(
        y_test,
        test["predicted_demand"]
    )
)

r2 = r2_score(
    y_test,
    test["predicted_demand"]
)


print("\n==============================")
print("FINAL MODEL PERFORMANCE")
print("==============================")

print(f"MAE:  {mae:.4f}")
print(f"RMSE: {rmse:.4f}")
print(f"R²:   {r2:.4f}")


# ============================================================
# 17. RESIDUAL / ABSOLUTE ERROR
# ============================================================

test["residual"] = (
    test["demand"]
    - test["predicted_demand"]
)

test["absolute_error"] = (
    test["residual"].abs()
)


# ============================================================
# 18. DEMAND LEVEL ERROR ANALYSIS
# ============================================================

bins = [
    0,
    5,
    10,
    50,
    100,
    200,
    500,
    np.inf
]

labels = [
    "0-5",
    "5-10",
    "10-50",
    "50-100",
    "100-200",
    "200-500",
    "500+"
]

test["demand_level"] = pd.cut(
    test["demand"],
    bins=bins,
    labels=labels,
    include_lowest=True
)


demand_analysis = (
    test.groupby(
        "demand_level",
        observed=True
    )
    .agg(

        observations=(
            "demand",
            "size"
        ),

        avg_demand=(
            "demand",
            "mean"
        ),

        avg_predicted_demand=(
            "predicted_demand",
            "mean"
        ),

        avg_residual=(
            "residual",
            "mean"
        ),

        mae=(
            "absolute_error",
            "mean"
        ),

        total_demand=(
            "demand",
            "sum"
        ),

        total_abs_error=(
            "absolute_error",
            "sum"
        )
    )
)


# ============================================================
# 19. NORMALIZED MAE
# ============================================================

demand_analysis["normalized_mae"] = (

    demand_analysis["total_abs_error"]
    /
    demand_analysis["total_demand"]

)


print("\n==============================")
print("ERROR BY DEMAND LEVEL")
print("==============================")

print(demand_analysis)


# ============================================================
# 20. OVER / UNDER PREDICTION ANALYSIS
# ============================================================

test["prediction_direction"] = np.where(

    test["predicted_demand"] > test["demand"],

    "Overprediction",

    "Underprediction"
)


direction_analysis = (
    test.groupby(
        "demand_level",
        observed=True
    )["prediction_direction"]
    .value_counts(normalize=True)
    .unstack(fill_value=0)
)


print("\n==============================")
print("OVER / UNDER PREDICTION")
print("==============================")

print(direction_analysis)


# ============================================================
# 21. HOLIDAY PERFORMANCE
# ============================================================

holiday_analysis = (
    test.groupby("is_holiday")
    .agg(

        observations=(
            "demand",
            "size"
        ),

        avg_demand=(
            "demand",
            "mean"
        ),

        avg_prediction=(
            "predicted_demand",
            "mean"
        ),

        mae=(
            "absolute_error",
            "mean"
        )
    )
)

print("\n==============================")
print("HOLIDAY ANALYSIS")
print("==============================")

print(holiday_analysis)


# ============================================================
# 22. EXTREME DEMAND ANALYSIS: 500+
# ============================================================

extreme = test[
    test["demand"] > 500
].copy()

if len(extreme) > 0:

    extreme_mae = extreme["absolute_error"].mean()

    extreme_nmae = (
        extreme["absolute_error"].sum()
        /
        extreme["demand"].sum()
    )

    extreme_underprediction_rate = (
        extreme["predicted_demand"]
        <
        extreme["demand"]
    ).mean()

    print("\n==============================")
    print("500+ DEMAND ANALYSIS")
    print("==============================")

    print(
        "Observations:",
        len(extreme)
    )

    print(
        f"MAE: {extreme_mae:.4f}"
    )

    print(
        f"NMAE: {extreme_nmae:.4%}"
    )

    print(
        "Underprediction rate:",
        f"{extreme_underprediction_rate:.2%}"
    )


# ============================================================
# 23. FEATURE IMPORTANCE
# ============================================================

importance = pd.DataFrame({

    "feature": features,

    "importance": model.feature_importances_

}).sort_values(
    "importance",
    ascending=False
)


print("\n==============================")
print("FEATURE IMPORTANCE")
print("==============================")

print(importance)


# ============================================================
# 24. SAVE RESULTS
# ============================================================

test_output = test[
    [
        "request_hour",
        "pickup_zone",
        "company",
        "demand",
        "predicted_demand",
        "residual",
        "absolute_error",
        "demand_level",
        "is_holiday"
    ]
]

test_output.to_csv(
    "final_model_predictions.csv",
    index=False
)

demand_analysis.to_csv(
    "final_model_demand_level_analysis.csv"
)

importance.to_csv(
    "final_model_feature_importance.csv",
    index=False
)

model.save_model(
    "final_xgboost_model.json"
)

print("\nFinal model and results saved.")


extreme_summary = (
    extreme.groupby(["pickup_zone"])
    .agg(
        observations=("demand", "size"),
        avg_demand=("demand", "mean"),
        avg_prediction=("predicted_demand", "mean"),
        avg_residual=("residual", "mean"),
        mae=("absolute_error", "mean")
    )
    .sort_values("observations", ascending=False)
)

print(extreme_summary.head(20))