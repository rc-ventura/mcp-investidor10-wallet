import json
import multiprocessing

import memory_worker

from investidor10_wallet.memory_store import MemoryStore

JOIN_TIMEOUT_SECONDS = 120


def _spawn(path, label, count):
    context = multiprocessing.get_context("spawn")
    process = context.Process(target=memory_worker.run, args=(path, label, count))
    process.start()
    return process


def _finish(*processes):
    for process in processes:
        process.join(JOIN_TIMEOUT_SECONDS)
        assert process.exitcode == 0


def test_two_processes_interleaving_writes_lose_nothing(tmp_path):
    path = str(tmp_path / "memory.json")
    MemoryStore(path)

    first = _spawn(path, "a", 100)
    second = _spawn(path, "b", 100)
    _finish(first, second)

    rules = MemoryStore(path).get_rules()
    assert len(rules) == 200
    assert len({rule["id"] for rule in rules}) == 200
    expected = {f"{label}-{index}" for label in "ab" for index in range(100)}
    assert {rule["text"] for rule in rules} == expected


def test_write_by_another_process_is_visible_without_restarting(tmp_path):
    path = str(tmp_path / "memory.json")
    reader = MemoryStore(path)
    assert reader.get_rules() == []

    _finish(_spawn(path, "other", 1))

    assert [rule["text"] for rule in reader.get_rules()] == ["other-0"]


def test_concurrent_writers_leave_one_intact_changelog_line_per_mutation(tmp_path):
    path = str(tmp_path / "memory.json")
    MemoryStore(path)

    first = _spawn(path, "a", 20)
    second = _spawn(path, "b", 20)
    _finish(first, second)

    with open(f"{path}.log", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 40
    assert {line["after"]["text"] for line in lines} == {
        f"{label}-{index}" for label in "ab" for index in range(20)
    }
