import numpy as np
import pandas as pd

import config
from src.algorithms.association_rules import (
    apriori_frequent_itemsets,
    build_transactions,
    discretise_value,
    generate_rules,
)


def mine_weather_rules(clean_wide, min_support=config.APRIORI_MIN_SUPPORT, min_confidence=config.APRIORI_MIN_CONFIDENCE):
    reference_rows = clean_wide.iloc[: int(len(clean_wide) * config.REFERENCE_PERIOD_FRACTION)]
    transactions = build_transactions(reference_rows)
    frequent_itemsets = apriori_frequent_itemsets(transactions, min_support)
    rules = generate_rules(frequent_itemsets, len(transactions), min_confidence)
    strong_rules = [
        rule
        for rule in rules
        if rule["lift"] > 1.05 and len(rule["antecedent"]) >= 1
    ]
    strong_rules.sort(key=lambda rule: -rule["lift"])
    return strong_rules


def build_state_vectors(wide_frame):
    state_columns = {}
    for sensor_name in config.SENSORS:
        state_columns[sensor_name] = wide_frame[sensor_name].map(
            lambda value, name=sensor_name: discretise_value(name, value)
        )
    return pd.DataFrame(state_columns, index=wide_frame.index)


def count_rule_violations(states, rules, max_rules=60):
    selected_rules = rules[:max_rules]
    violation_counts = np.zeros(len(states), dtype=float)
    for rule in selected_rules:
        antecedent = rule["antecedent"]
        consequent = rule["consequent"]
        antecedent_hits = np.ones(len(states), dtype=bool)
        for item in antecedent:
            column_name, state_name = item.rsplit("_", 1)
            if column_name not in states.columns:
                antecedent_hits[:] = False
                break
            antecedent_hits &= states[column_name].to_numpy() == item
        if not antecedent_hits.any():
            continue
        consequent_item = next(iter(consequent))
        consequent_column, _ = consequent_item.rsplit("_", 1)
        if consequent_column not in states.columns:
            continue
        consequent_hits = states[consequent_column].to_numpy() == consequent_item
        violation_counts += (antecedent_hits & ~consequent_hits).astype(float)
    return violation_counts


def rule_violations_for_wide(wide_frame, rules):
    states = build_state_vectors(wide_frame)
    violations = count_rule_violations(states, rules)
    return pd.Series(violations, index=wide_frame.index)
