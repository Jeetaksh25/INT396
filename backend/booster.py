import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, cross_val_predict

TREES = 100


def make_booster():
    return RandomForestClassifier(n_estimators=TREES, min_samples_leaf=2, max_depth=20, n_jobs=-1, random_state=42)


def boost(X, y, stations, path):
    proba = cross_val_predict(make_booster(), X, y, groups=stations, cv=GroupKFold(n_splits=4), method="predict_proba")
    order = sorted(y.unique())
    booster = make_booster().fit(X, y)
    joblib.dump(booster, path)
    predicted = np.array(order)[proba.argmax(axis=1)]
    confidence = 1 - proba[:, order.index("normal")]
    return predicted, confidence, booster
