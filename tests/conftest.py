import os
import tempfile

os.environ.setdefault("WALLET_ID", "2061045")
_test_dir = tempfile.mkdtemp(prefix="mcp-investidor10-tests-")
os.environ["WALLET_MEMORY_PATH"] = os.path.join(_test_dir, "memory.json")
