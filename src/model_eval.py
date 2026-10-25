"""Model comparison for the proposal table: validation by cross-validation on a
training split, and a single evaluation on a held-out test split.

Spain: target is a field's mean grade minus its university-year average; the
test set is 20% of universities, never seen in training.
Portugal: target is the first-year grade average; the test set is 20% of
students, stratified by degree.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.metrics import root_mean_squared_error
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, KFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from analysis import CONTROLS
from load_data import ROOT, load_clean
from ministry import load as load_spain

SEED = 42
ALPHAS = np.logspace(-3, 3, 25)


def preprocessor(num: list[str], cat: list[str]) -> ColumnTransformer:
    parts = []
    if num:
        parts.append(("num", StandardScaler(), num))
    if cat:
        parts.append(("cat", OneHotEncoder(handle_unknown="ignore"), cat))
    return ColumnTransformer(parts)


def evaluate(models: dict, X_tr, y_tr, X_te, y_te, cv, groups=None) -> dict:
    out = {}
    for name, model in models.items():
        s = -cross_val_score(model, X_tr, y_tr, cv=cv, groups=groups, scoring="neg_root_mean_squared_error")
        model.fit(X_tr, y_tr)
        out[name] = {"cv_rmse_mean": float(s.mean()), "cv_rmse_sd": float(s.std(ddof=1)),
                     "test_rmse": float(root_mean_squared_error(y_te, model.predict(X_te)))}
    return out


def spain() -> dict:
    df = load_spain()
    df["y"] = df["mean"] - df.groupby(["univ", "year"])["mean"].transform("mean")
    tr_idx, te_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED).split(df, groups=df["univ"]))
    tr, te = df.iloc[tr_idx], df.iloc[te_idx]
    models = {
        "baseline: zero deviation (field ignored)": DummyRegressor(strategy="constant", constant=0.0),
        "ridge: field of study": make_pipeline(preprocessor([], ["field"]), RidgeCV(alphas=ALPHAS)),
    }
    res = evaluate(models, tr, tr["y"], te, te["y"], GroupKFold(n_splits=10), groups=tr["univ"])
    return {"n_train": len(tr), "n_test": len(te), "n_univ_train": int(tr["univ"].nunique()),
            "n_univ_test": int(te["univ"].nunique()), "models": res}


def portugal() -> dict:
    df = load_clean()
    tr, te = train_test_split(df, test_size=0.2, random_state=SEED, stratify=df["course"])
    models = {
        "baseline: overall mean": DummyRegressor(strategy="mean"),
        "linear: entry grades + background": make_pipeline(preprocessor(CONTROLS, []), LinearRegression()),
        "linear: degree only": make_pipeline(preprocessor([], ["course"]), LinearRegression()),
        "ridge: entry grades + background + degree": make_pipeline(
            preprocessor(CONTROLS, ["course"]), RidgeCV(alphas=ALPHAS)),
    }
    res = evaluate(models, tr, tr["gpa"], te, te["gpa"], KFold(n_splits=10, shuffle=True, random_state=SEED))
    return {"n_train": len(tr), "n_test": len(te), "models": res}


def main() -> None:
    out = {"spain": spain(), "portugal": portugal()}
    (ROOT / "results" / "model_comparison.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
