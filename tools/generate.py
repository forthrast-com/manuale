"""Generate deterministic, compressed day packs for a fully static host."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import re

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
def generator_hash():
    """What a day pack's bytes actually depend on, and nothing else.

    Hashing this whole file made every index-only edit invalidate two years of
    packs whose contents had not changed. Hash the importer, the pinned source,
    the corrections, and the recipe that shapes a pack: the body of
    generate_day together with the constants it reads.
    """
    recipe = inspect.getsource(generate_day) + repr((SCHEMA, HOURS, sorted(VOTIVES)))
    return hashlib.sha256(
        (ROOT / "tools/liturgy.py").read_bytes()
        + (ROOT / "source_patches.json").read_bytes()
        + (ROOT / "sources.json").read_bytes()
        + recipe.encode()
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


# The Mass is ordinary where it does not change and proper where it does, so
# the corpus can say which is which rather than a list of Latin incipits doing
# it from memory. The distribution is bimodal and the gap is enormous: over a
# year, 4622 blocks fall below 10% of days and 221 above 90%, leaving 9 in
# between. Those nine put the boundary between the common preface at 39.5%,
# which a propers sheet prints, and the Gloria's rubrics at 68.8%, which it
# does not. Half the days is the natural line through that gap.
# Votive and numbered Masses are excluded from the count: their propers repeat
# daily by nature and would be mistaken for the ordinary.
ORDINARY_SHARE = 0.5
VARYING_RITES = ("Missa", "MissaLecta")


def block_text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def block_id(html):
    """FNV-1a 64, so the browser can recompute it without a crypto call."""
    digest = 0xcbf29ce484222325
    for byte in block_text(html).encode():
        digest = ((digest ^ byte) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return f"{digest:016x}"


def ordinary_ids(payloads):
    ordinary = set()
    for kind in VARYING_RITES:
        seen, days = Counter(), 0
        for payload in payloads:
            rite = payload["rites"].get(kind)
            if not rite:
                continue
            days += 1
            seen.update({block_id(block["html"])
                         for section in rite["sections"] for block in section["blocks"]})
        if days:
            ordinary |= {i for i, n in seen.items() if n >= days * ORDINARY_SHARE}
    return sorted(ordinary)


GENERATOR = generator_hash()


def write_index():
    days = {}
    payloads = []
    for path in sorted((OUTPUT / "days").glob("*.json.gz")):
        packed = path.read_bytes()
        payload = json.loads(gzip.decompress(packed))
        # The generator hash covers sources.json, source_patches.json and this
        # file, so it already subsumes the revision and the schema. A pack that
        # fails it belongs to an older pin and is simply not ours to publish;
        # restored artifacts and rolled-forward years both leave such packs
        # lying about. A pack that claims our generator but disagrees about
        # either is a real contradiction, and says so.
        if payload.get("generator") != GENERATOR:
            continue
        if payload["source"] != SPEC["revision"] or payload["schema"] != SCHEMA:
            raise ValueError(f"Pack contradicts its own generator: {path}")
        mass = payload["rites"]["Missa"]
        payloads.append(payload)
        days[payload["date"]] = {"title": mass["title"], "rank": mass["rank"],
                                 "bytes": len(packed), "sha256": hashlib.sha256(packed).hexdigest()}
    index = {"schema": SCHEMA, "source": SPEC, "votives": VOTIVES,
             "ordinary": ordinary_ids(payloads), "days": days}
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
