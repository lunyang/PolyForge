from __future__ import annotations

from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression


SUPPORTED_MODELS = ("mean", "linear_regression", "random_forest")


def make_estimator(model_name: str, *, random_state: int = 0):
    if model_name == "mean":
        return DummyRegressor(strategy="mean")
    if model_name == "linear_regression":
        return LinearRegression()
    if model_name == "random_forest":
        return RandomForestRegressor(
            n_estimators=200,
            random_state=random_state,
            n_jobs=1,
        )
    raise ValueError(f"unsupported model: {model_name}")
