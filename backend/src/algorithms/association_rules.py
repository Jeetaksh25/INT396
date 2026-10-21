import math


def discretise_value(sensor_name, value):
    value = float(value)

    if sensor_name == "temperature":
        if value < 15.0:
            return "temperature_cold"
        if value > 30.0:
            return "temperature_hot"
        return "temperature_normal"

    if sensor_name == "humidity":
        if value < 40.0:
            return "humidity_dry"
        if value > 70.0:
            return "humidity_wet"
        return "humidity_normal"

    if sensor_name == "wind_speed":
        if value < 12.0:
            return "wind_speed_calm"
        if value > 30.0:
            return "wind_speed_windy"
        return "wind_speed_breezy"

    if sensor_name == "pressure":
        if value < 1000.0:
            return "pressure_low"
        if value > 1015.0:
            return "pressure_high"
        return "pressure_normal"

    raise ValueError("unknown sensor: " + str(sensor_name))


def build_transactions(wide_frame):
    transactions = []
    columns = ["temperature", "humidity", "wind_speed", "pressure"]
    values = {column: wide_frame[column].to_numpy() for column in columns}
    n_rows = len(values["temperature"])

    for row in range(n_rows):
        transaction = set()
        for column in columns:
            transaction.add(discretise_value(column, values[column][row]))
        transactions.append(transaction)
    return transactions


def _minimum_support_count(min_support, transactions_count):
    threshold = min_support * transactions_count
    return max(1, int(math.ceil(threshold - 1e-12)))


def _count_support(transactions, itemset):
    count = 0
    for transaction in transactions:
        if itemset.issubset(transaction):
            count += 1
    return count


def apriori_frequent_itemsets(transactions, min_support):
    transactions_count = len(transactions)
    minimum_count = _minimum_support_count(min_support, transactions_count)

    item_counts = {}
    for transaction in transactions:
        for item in transaction:
            item_counts[item] = item_counts.get(item, 0) + 1

    current_level = {}
    for item, count in item_counts.items():
        if count >= minimum_count:
            current_level[frozenset([item])] = count / transactions_count

    frequent_itemsets = dict(current_level)

    while current_level:
        previous_items = [itemset for itemset in current_level]
        previous_items.sort(key=lambda itemset: sorted(itemset))

        candidates = set()
        for first_index in range(len(previous_items)):
            for second_index in range(first_index + 1, len(previous_items)):
                union = previous_items[first_index] | previous_items[second_index]
                if len(union) == len(previous_items[first_index]) + 1:
                    candidates.add(union)

        next_level = {}
        for candidate in candidates:
            parts = [frozenset([item]) for item in candidate]
            pruned = False
            for part in parts:
                remainder = candidate - part
                if remainder not in frequent_itemsets:
                    pruned = True
                    break
            if pruned:
                continue
            count = _count_support(transactions, candidate)
            if count >= minimum_count:
                next_level[candidate] = count / transactions_count

        frequent_itemsets.update(next_level)
        current_level = next_level

    return frequent_itemsets


class _FPTreeNode:
    def __init__(self, item, parent):
        self.item = item
        self.parent = parent
        self.count = 0
        self.children = {}


def _insert_path(root, items, count, header):
    node = root
    for item in items:
        if item not in node.children:
            child = _FPTreeNode(item, node)
            node.children[item] = child
            header[item].append(child)
        node = node.children[item]
        node.count += count


def _mine_tree(node, prefix, header, minimum_count, transactions_count, results):
    items = sorted(header.items(), key=lambda pair: (-pair[1][0].count, pair[0]))
    for item, nodes in items:
        new_prefix = prefix | frozenset([item])
        total_count = sum(header_node.count for header_node in nodes)
        results[new_prefix] = total_count / transactions_count

        conditional_paths = []
        for header_node in nodes:
            path = []
            walker = header_node.parent
            while walker is not None and walker.parent is not None:
                path.append(walker.item)
                walker = walker.parent
            if path:
                conditional_paths.append((path, header_node.count))

        if not conditional_paths:
            continue

        conditional_counts = {}
        for path, count in conditional_paths:
            for path_item in path:
                conditional_counts[path_item] = conditional_counts.get(path_item, 0) + count

        ordered_items = [value for value, count in conditional_counts.items() if count >= minimum_count]
        if not ordered_items:
            continue
        ordered_items.sort(key=lambda value: (-conditional_counts[value], value))

        conditional_root = _FPTreeNode(None, None)
        conditional_header = {value: [] for value in ordered_items}
        for path, count in conditional_paths:
            filtered = [value for value in ordered_items if value in path]
            if filtered:
                _insert_path(conditional_root, filtered, count, conditional_header)
        if conditional_root.children:
            _mine_tree(conditional_root, new_prefix, conditional_header, minimum_count, transactions_count, results)


def fpgrowth_frequent_itemsets(transactions, min_support):
    transactions_count = len(transactions)
    minimum_count = _minimum_support_count(min_support, transactions_count)

    item_counts = {}
    for transaction in transactions:
        for item in transaction:
            item_counts[item] = item_counts.get(item, 0) + 1

    frequent_items = {item: count for item, count in item_counts.items() if count >= minimum_count}
    if not frequent_items:
        return {}

    order_key = lambda item: (-frequent_items[item], item)
    ordered_items = sorted(frequent_items, key=order_key)
    item_order = {item: position for position, item in enumerate(ordered_items)}

    root = _FPTreeNode(None, None)
    header = {item: [] for item in ordered_items}
    for transaction in transactions:
        filtered = [item for item in transaction if item in frequent_items]
        filtered.sort(key=lambda item: item_order[item])
        if filtered:
            _insert_path(root, filtered, 1, header)

    results = {}
    _mine_tree(root, frozenset(), header, minimum_count, transactions_count, results)
    for item, count in frequent_items.items():
        results[frozenset([item])] = count / transactions_count
    return results


def generate_rules(frequent_itemsets, transactions_count, min_confidence):
    supports = {}
    for itemset, support in frequent_itemsets.items():
        supports[itemset] = support

    rules = []
    for itemset, support in frequent_itemsets.items():
        if len(itemset) < 2:
            continue
        for consequent_item in itemset:
            consequent = frozenset([consequent_item])
            antecedent = itemset - consequent
            if not antecedent:
                continue
            if antecedent not in supports or consequent not in supports:
                continue

            antecedent_support = supports[antecedent]
            consequent_support = supports[consequent]
            if antecedent_support <= 0.0:
                continue

            confidence = support / antecedent_support
            if confidence < min_confidence:
                continue

            if consequent_support <= 0.0:
                lift = 0.0
            else:
                lift = confidence / consequent_support

            if confidence >= 1.0:
                conviction = 999.0
            else:
                conviction = (1.0 - consequent_support) / (1.0 - confidence)

            rules.append(
                {
                    "antecedent": antecedent,
                    "consequent": consequent,
                    "support": float(support),
                    "confidence": float(confidence),
                    "lift": float(lift),
                    "conviction": float(conviction),
                }
            )

    rules.sort(key=lambda rule: (-rule["confidence"], -rule["support"]))
    return rules
