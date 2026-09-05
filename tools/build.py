"""Build a subdirectory-safe static PWA; no Node packages or runtime backend."""

import hashlib
import json
from pathlib import Path
import shutil
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def png_icon(size):
    def chunk(name, value):
        return struct.pack(">I", len(value)) + name + value + struct.pack(">I", zlib.crc32(name + value))
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            cross = (238 / 512 <= x / size < 274 / 512 and 132 / 512 <= y / size < 380 / 512) or (153 / 512 <= x / size < 359 / 512 and 227 / 512 <= y / size < 263 / 512)
            rows.extend((250, 249, 247) if cross else (128, 58, 53))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


def main():
    if not (ROOT / "data/index.json").exists():
        raise SystemExit("Generate liturgical data first: make data")
    DIST.mkdir(exist_ok=True)
    index = json.loads((ROOT / "data/index.json").read_text())
    for day, info in index["days"].items():
        path = ROOT / "data/days" / f"{day}.json.gz"
        if hashlib.sha256(path.read_bytes()).hexdigest() != info["sha256"]:
            raise SystemExit(f"Stale data index for {day}; finish generation before building.")
    # Rebuild the shell from scratch: a leftover file would otherwise be served
    # and precached forever. Day packs are kept and reconciled below.
    packs = DIST / "data/days"
    for path in sorted(DIST.rglob("*"), key=lambda path: len(path.parts), reverse=True):
        if path == packs or packs in path.parents:
            continue
        path.unlink() if path.is_file() else path.rmdir() if not any(path.iterdir()) else None
    shutil.copytree(ROOT / "src", DIST, dirs_exist_ok=True)
    packs.mkdir(parents=True, exist_ok=True)
    for day in index["days"]:
        shutil.copy2(ROOT / "data/days" / f"{day}.json.gz", packs / f"{day}.json.gz")
    for path in packs.glob("*.json.gz"):
        # A day dropped from the index must not linger as an unreachable file.
        if path.name.removesuffix(".json.gz") not in index["days"]:
            path.unlink()
    shutil.copy2(ROOT / "data/index.json", DIST / "data/index.json")
    icons = DIST / "icons"
    icons.mkdir(exist_ok=True)
    for filename, size in [("icon-192.png", 192), ("icon-512.png", 512), ("apple-touch-icon.png", 180)]:
        (icons / filename).write_bytes(png_icon(size))
    licence = (ROOT / "vendor/divinum-officium/LICENSE").read_text()
    font_licence = (ROOT / "src/fonts/OFL.txt").read_text() + "\n\nIM FELL English — Igino Marini\n\n" + (ROOT / "src/fonts/IM_FELL_OFL.txt").read_text()
    (DIST / "licences.txt").write_text("Manuale uses Divinum Officium, including its Latin text corpus.\n\n"
        "The Manuale application code was written with AI assistance (OpenAI GPT\n"
        "and Anthropic Claude models) under human review. The liturgical text was\n"
        "not: it is imported verbatim from Divinum Officium at the pinned revision.\n\n" + licence + "\n\nFraunces display font — Undercase Type\n\n" + font_licence)
    (DIST / ".nojekyll").touch()
    # cache.addAll is all-or-nothing: one absent entry costs the whole offline
    # shell, so never precache incidental dotfiles such as .DS_Store.
    assets = sorted(
        str(path.relative_to(DIST)) for path in DIST.rglob("*")
        if path.is_file() and path.name != "sw.js" and "days" not in path.parts
        and not any(part.startswith(".") for part in path.relative_to(DIST).parts)
    )
    digest = hashlib.sha256()
    for asset in assets:
        digest.update(asset.encode())
        digest.update((DIST / asset).read_bytes())
    version = digest.hexdigest()[:16]
    worker = (ROOT / "src/sw.js").read_text().replace("__BUILD_VERSION__", version).replace("__PRECACHE_ASSETS__", json.dumps(assets))
    (DIST / "sw.js").write_text(worker)
    print(f"Built dist/ · {len(assets)} shell assets · version {version}")


if __name__ == "__main__":
    main()
