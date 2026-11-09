import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent / "ping-plugin" / "servers" / "ping.mcpb"
FILES = ("manifest.json", "pyproject.toml", "server/main.py")
FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def build() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(FILES):
            info = zipfile.ZipInfo(name, FIXED_DATE)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (HERE / name).read_bytes())


if __name__ == "__main__":
    build()
