from investidor10_wallet.memory_store import MemoryStore


def run(path, label, count):
    store = MemoryStore(path)
    for index in range(count):
        store.save_rule(f"{label}-{index}")


def evaluate(path, quotes):
    MemoryStore(path).evaluate_alerts(quotes)
