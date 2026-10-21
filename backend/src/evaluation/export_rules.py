import json

import config
from src.features.rule_features import mine_weather_rules
from src.algorithms.association_rules import (
    apriori_frequent_itemsets,
    build_transactions,
    fpgrowth_frequent_itemsets,
)


def serialise_rule(rule):
    return {
        "antecedent": sorted(rule["antecedent"]),
        "consequent": sorted(rule["consequent"]),
        "support": round(rule["support"], 4),
        "confidence": round(rule["confidence"], 4),
        "lift": round(rule["lift"], 4),
        "conviction": round(rule["conviction"], 4) if rule["conviction"] != float("inf") else None,
    }


def main():
    import pandas as pd
    import time

    clean_wide = pd.read_parquet(config.PROCESSED_DIR / "clean_wide.parquet")
    rules = mine_weather_rules(clean_wide)
    reference = clean_wide.iloc[: int(len(clean_wide) * config.REFERENCE_PERIOD_FRACTION)]
    transactions = build_transactions(reference)

    start = time.time()
    apriori_itemsets = apriori_frequent_itemsets(transactions, config.APRIORI_MIN_SUPPORT)
    apriori_seconds = time.time() - start

    start = time.time()
    fpgrowth_itemsets = fpgrowth_frequent_itemsets(transactions, config.APRIORI_MIN_SUPPORT)
    fpgrowth_seconds = time.time() - start

    payload = {
        "transactions": len(transactions),
        "min_support": config.APRIORI_MIN_SUPPORT,
        "min_confidence": config.APRIORI_MIN_CONFIDENCE,
        "rule_count": len(rules),
        "rules": [serialise_rule(rule) for rule in rules],
        "algorithm_comparison": {
            "apriori_itemsets": len(apriori_itemsets),
            "fpgrowth_itemsets": len(fpgrowth_itemsets),
            "itemsets_match": apriori_itemsets == fpgrowth_itemsets,
            "apriori_seconds": round(apriori_seconds, 4),
            "fpgrowth_seconds": round(fpgrowth_seconds, 4),
        },
    }

    with open(config.RESULTS_DIR / "association_rules.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    print(json.dumps(payload["algorithm_comparison"], indent=2))
    print(f"wrote {payload['rule_count']} rules")


if __name__ == "__main__":
    main()
