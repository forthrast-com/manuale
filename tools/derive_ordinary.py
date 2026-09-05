"""Rebuild the ordinary classification from a fixed, complete calendar year."""

from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
import gzip
import json

import generate
from liturgy import ROOT, SPEC, render_rite

REFERENCE_YEAR = 2026


def reference_day(day):
    # Reuse verified packs when available; a fresh checkout only renders the
    # two Mass forms, without generating or publishing unrelated Office packs.
    path = generate.OUTPUT / "days" / f"{day.isoformat()}.json.gz"
    if path.exists():
        payload = json.loads(gzip.decompress(path.read_bytes()))
        if (payload.get("generator") == generate.GENERATOR
                and payload.get("source") == SPEC["revision"]
                and payload.get("schema") == generate.SCHEMA
                and payload.get("date") == day.isoformat()):
            return payload
    return {"rites": {kind: render_rite(day, kind) for kind in generate.VARYING_RITES}}


def main():
    start, end = date(REFERENCE_YEAR, 1, 1), date(REFERENCE_YEAR + 1, 1, 1)
    days = [start + timedelta(days=n) for n in range((end - start).days)]
    with ProcessPoolExecutor(max_workers=4) as pool:
        payloads = list(pool.map(reference_day, days))
    reference = {
        "year": REFERENCE_YEAR,
        "source": SPEC["revision"],
        "generator": generate.GENERATOR,
        "recipe": generate.reference_recipe(),
        "ordinary": generate.ordinary_ids(payloads),
    }
    (ROOT / "ordinary_reference.json").write_text(json.dumps(reference, indent=2) + "\n")
    print(f"Derived {len(reference['ordinary'])} ordinary blocks from {len(days)} days")


if __name__ == "__main__":
    main()
