"""Fetch a pinned, minimal Divinum Officium checkout; never update it silently."""

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "vendor" / "divinum-officium"
SPEC = json.loads((ROOT / "sources.json").read_text())
DIRECTORIES = [
    "web/cgi-bin",
    "web/www/Tabulae",
    "web/www/horas/Latin",
    "web/www/horas/English",
    "web/www/horas/Ordinarium",
    "web/www/missa/Latin",
    "web/www/missa/English",
    "standalone/tools/epubgen2",
]


def git(*args, capture=False):
    return subprocess.run(
        ["git", "-C", str(SOURCE), *args], check=True,
        text=True, capture_output=capture,
    ).stdout


def head():
    """The checked-out revision, or None before the first checkout.

    git init writes .git/HEAD straight away, so the file's existence says
    nothing about whether a commit is there to resolve.
    """
    result = subprocess.run(
        ["git", "-C", str(SOURCE), "rev-parse", "--verify", "--quiet", "HEAD"],
        text=True, capture_output=True,
    )
    return result.stdout.strip() or None


def main():
    if not (SOURCE / ".git").is_dir():
        SOURCE.mkdir(parents=True, exist_ok=True)
        git("init")
        git("remote", "add", "origin", SPEC["repository"])
    # A restored CI cache may hold a previous pin. Moving an existing checkout
    # to the pinned revision must work without deleting vendor/ by hand.
    git("remote", "set-url", "origin", SPEC["repository"])
    git("sparse-checkout", "init", "--cone")
    git("sparse-checkout", "set", *DIRECTORIES)
    if head() != SPEC["revision"]:
        git("fetch", "--depth", "1", "origin", SPEC["revision"])
        # Discards the previous revision's applied corrections along with it.
        git("checkout", "--detach", "--force", SPEC["revision"])
    revision = head()
    if revision != SPEC["revision"]:
        raise SystemExit(f"Source revision mismatch: {revision}; expected {SPEC['revision']}")
    for directory in DIRECTORIES:
        if not (SOURCE / directory).is_dir():
            raise SystemExit(f"Incomplete source checkout: {directory}")
    if not (SOURCE / "LICENSE").is_file():
        raise SystemExit("Incomplete source checkout: LICENSE (bundled into the build)")
    for patch in json.loads((ROOT / "source_patches.json").read_text()):
        path = SOURCE / patch["path"]
        original = path.read_text()
        if patch["before"] in original:
            if original.count(patch["before"]) != 1:
                raise SystemExit(f"Ambiguous source correction: {path}")
            path.write_text(original.replace(patch["before"], patch["after"]))
        elif patch["after"] not in original:
            raise SystemExit(f"Source correction no longer applies: {path}")
    print(f"Divinum Officium {revision[:12]}")


if __name__ == "__main__":
    main()
