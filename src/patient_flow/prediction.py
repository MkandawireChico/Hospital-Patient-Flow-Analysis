from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from patient_flow.analysis import filter_analysis_frame


TARGET_COLUMN = "Long_Wait_Target"
DEFAULT_FEATURES = [
    "Department",
    "Priority_Level",
    "Visit_Type",
    "Arrival_Hour",
    "Arrival_Day_Of_Week",
    "Arrival_Month",
]


def prepare_prediction_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Build a leakage-conscious feature matrix and >60-minute target.

    Only encounter descriptors and arrival-time features are used. Wait components, total wait,
    length of stay, disposition, and post-arrival process outcomes are deliberately excluded.
    """
    analysis = filter_analysis_frame(df)
    wait_column = (
        "Total_Waiting_Time_Valid"
        if "Total_Waiting_Time_Valid" in analysis.columns
        else "Total_Waiting_Time"
    )
    waits = pd.to_numeric(analysis[wait_column], errors="coerce")
    valid = waits.notna()
    analysis = analysis.loc[valid].copy()
    waits = waits.loc[valid]
    target = waits.gt(60.0).astype(int).rename("Long_Wait_Target")

    if "Arrival_Hour" not in analysis.columns and "Arrival_Time" in analysis.columns:
        analysis["Arrival_Hour"] = pd.to_datetime(
            analysis["Arrival_Time"], errors="coerce"
        ).dt.hour
    if "Arrival_Day_Of_Week" not in analysis.columns:
        if "Arrival_Time" in analysis.columns:
            analysis["Arrival_Day_Of_Week"] = pd.to_datetime(
                analysis["Arrival_Time"], errors="coerce"
            ).dt.dayofweek
        elif "Visit_Date" in analysis.columns:
            analysis["Arrival_Day_Of_Week"] = pd.to_datetime(
                analysis["Visit_Date"], errors="coerce"
            ).dt.dayofweek
    if "Arrival_Month" not in analysis.columns:
        date_column = "Arrival_Time" if "Arrival_Time" in analysis.columns else "Visit_Date"
        if date_column in analysis.columns:
            analysis["Arrival_Month"] = pd.to_datetime(
                analysis[date_column], errors="coerce"
            ).dt.month

    available = [column for column in DEFAULT_FEATURES if column in analysis.columns]
    if not available:
        raise ValueError("No eligible pre-outcome features are available for long-wait modelling")

    features = analysis[available].copy()
    categorical = [column for column in available if features[column].dtype == "object" or
                   isinstance(features[column].dtype, pd.StringDtype)]
    numeric = [column for column in available if column not in categorical]
    for column in categorical:
        features[column] = features[column].astype("string")
    for column in numeric:
        features[column] = pd.to_numeric(features[column], errors="coerce")

    return features, target


def train_long_wait_model(
    df: pd.DataFrame,
    *,
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, Any]:
    """Train and evaluate a class-weighted logistic regression on a held-out test set."""
    if not 0.1 <= test_size <= 0.5:
        raise ValueError("test_size must be between 0.1 and 0.5")

    features, target = prepare_prediction_frame(df)
    class_counts = target.value_counts()
    if len(class_counts) != 2 or int(class_counts.min()) < 2:
        raise ValueError("At least two examples from each long-wait class are required")

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_state,
        stratify=target,
    )
    categorical = [
        column
        for column in features.columns
        if features[column].dtype == "string" or features[column].dtype == "object"
    ]
    numeric = [column for column in features.columns if column not in categorical]

    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            )
        )
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            )
        )

    preprocessor = ColumnTransformer(transformers=transformers)
    model = Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1_000,
                    class_weight="balanced",
                    random_state=random_state,
                ),
            ),
        ]
    )
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
    fpr, tpr, thresholds = roc_curve(y_test, probabilities)

    metrics = {
        "observations": int(len(features)),
        "train_observations": int(len(x_train)),
        "test_observations": int(len(x_test)),
        "long_wait_prevalence_pct": float(target.mean() * 100),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "average_precision": float(average_precision_score(y_test, probabilities)),
        "threshold": 0.5,
        "true_negatives": int(matrix[0, 0]),
        "false_positives": int(matrix[0, 1]),
        "false_negatives": int(matrix[1, 0]),
        "true_positives": int(matrix[1, 1]),
        "features_used": ", ".join(features.columns),
        "split": "stratified random hold-out",
    }

    transformed_names = model.named_steps["preprocessor"].get_feature_names_out()
    coefficients = model.named_steps["classifier"].coef_[0]
    feature_effects = pd.DataFrame(
        {"feature": transformed_names, "coefficient": coefficients}
    )
    feature_effects["absolute_coefficient"] = feature_effects["coefficient"].abs()
    feature_effects = feature_effects.sort_values(
        "absolute_coefficient", ascending=False
    ).reset_index(drop=True)

    curve = pd.DataFrame(
        {
            "false_positive_rate": fpr,
            "true_positive_rate": tpr,
            "threshold": thresholds,
        }
    )
    return {
        "model": model,
        "metrics": metrics,
        "feature_effects": feature_effects,
        "roc_curve": curve,
        "test_target": y_test.reset_index(drop=True),
        "test_probability": pd.Series(probabilities),
    }
