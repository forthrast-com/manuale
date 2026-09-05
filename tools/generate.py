"""Generate deterministic, compressed day packs for a fully static host."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
import gzip
import hashlib
import json
from pathlib import Path

from liturgy import HOURS, ROOT, SPEC, render_rite

OUTPUT = ROOT / "data"
SCHEMA = 1
VOTIVES = {
    "C11": "De Beata Maria Virgine",
    "C9": "Pro defunctis",
    "V4": "De sancto Ioseph",
    "V6": "De Passione Domini",
    "Propaganda": "Pro propagatione fidei",
}
GENERATOR = hashlib.sha256(
    (ROOT / "tools/liturgy.py").read_bytes()
    + Path(__file__).read_bytes()
    + (ROOT / "source_patches.json").read_bytes()
    + (ROOT / "sources.json").read_bytes()
).hexdigest()


def generate_day(day):
    output = OUTPUT / "days" / f"{day.isoformat()}.json.gz"
    if output.exists():
        packed = output.read_bytes()
        previous = json.loads(gzip.decompress(packed))
        if previous.get("generator") == GENERATOR and previous.get("source") == SPEC["revision"]:
            return day.isoformat(), len(packed)
    rites = {"Missa": render_rite(day, "Missa"), "MissaLecta": render_rite(day, "MissaLecta")}
    rites |= {hour: render_rite(day, hour) for hour in HOURS}
    # Public celebration and private recitation have different greetings.
    rites |= {f"{hour}Choro": render_rite(day, hour, priest=True) for hour in HOURS}
    for code in VOTIVES:
        for kind in ("Missa", "MissaLecta"):
            rites[f"{kind}-{code}"] = render_rite(day, kind, votive=code)
    if (day.month, day.day) in {(12, 25), (11, 2)}:
        for number in (2, 3):
            for kind in ("Missa", "MissaLecta"):
                rites[f"{kind}{number}"] = render_rite(day, kind, missanumber=number)
    payload = {"schema": SCHEMA, "date": day.isoformat(), "source": SPEC["revision"], "generator": GENERATOR, "rites": rites}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    packed = gzip.compress(encoded, compresslevel=9, mtime=0)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_suffix(".pending")
    staging.write_bytes(packed)
    staging.replace(output)
    return day.isoformat(), len(packed)


def write_index():
    days = {}
    for path in sorted((OUTPUT / "days").glob("*.json.gz")):
        packed = path.read_bytes()
        payload = json.loads(gzip.decompress(packed))
        if payload["source"] != SPEC["revision"] or payload["schema"] != SCHEMA:
            raise ValueError(f"Stale data: {path}")
        if payload.get("generator") != GENERATOR:
            continue
        mass = payload["rites"]["Missa"]
        days[payload["date"]] = {"title": mass["title"], "rank": mass["rank"],
                                 "bytes": len(packed), "sha256": hashlib.sha256(packed).hexdigest()}
    index = {"schema": SCHEMA, "source": SPEC, "votives": VOTIVES, "days": days}
    (OUTPUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(date.today().year, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(date.today().year + 1, 12, 31))
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    if args.end < args.start:
        parser.error("--end must not precede --start")
    days = [args.start + timedelta(days=i) for i in range((args.end - args.start).days + 1)]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for index, (day, size) in enumerate(pool.map(generate_day, days), 1):
            if index % 20 == 0 or index == len(days):
                print(f"{index}/{len(days)} {day}: {size / 1024:.0f} KiB", flush=True)
    write_index()
    print(f"Saved {len(days)} complete days to {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
