"""A narrow boundary around Divinum Officium's pinned standalone renderers.

Calendar decisions belong to upstream. We only turn the fully expanded Latin
output into safe, reflowable blocks and expand the omitted Communion popup.
"""

import html
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode

from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "vendor/divinum-officium"
SPEC = json.loads((ROOT / "sources.json").read_text())
HOURS = ["Matutinum", "Laudes", "Prima", "Tertia", "Sexta", "Nona", "Vespera", "Completorium"]
ALLOWED_TAGS = {"span", "b", "strong", "em", "i", "sup", "br"}
CLASSES = {"ri": "rubric", "rd": "cross", "a": "initial", "w": "rubric"}


def plain(value):
    return BeautifulSoup(value, "html.parser").get_text("", strip=False).strip()


def sanitise(value):
    soup = BeautifulSoup(value, "html.parser")
    for tag in list(soup.find_all(True)):
        if tag.name in {"script", "style", "iframe", "object", "input", "button"}:
            tag.decompose()
        elif tag.name not in ALLOWED_TAGS:
            tag.unwrap()
        else:
            classes = [CLASSES[c] for c in tag.get("class", []) if c in CLASSES]
            if tag.name == "span" and re.fullmatch(r"\d+(?::\d+)?", tag.get_text().strip()):
                classes = ["verse-number"]
            if tag.name == "span" and tag.get_text().strip() in {"℣.", "℟.", "S.", "M.", "D.", "Ant.", "Ps."}:
                classes = ["versicle"]
            tag.attrs = {"class": list(dict.fromkeys(classes))} if classes else {}
    return str(soup).strip()


def block(value):
    value = sanitise(value)
    text = plain(value)
    if not text:
        return None
    fragment = BeautifulSoup(value, "html.parser")
    spoken = BeautifulSoup(value, "html.parser")
    for rubric in spoken.select(".rubric, .verse-number"):
        rubric.decompose()
    kind = "rubric" if not spoken.get_text().strip() else "prayer"
    # Source-location annotations ({ex Proprio de Tempore} and friends) tell a
    # reader which book the text was drawn from. They are neither prayer nor
    # rubric, so they get their own kind and stay out of the reading by default.
    if text.startswith("{") and text.endswith("}"):
        kind = "source"
    if fragment.select_one(".verse-number"):
        kind = "verse"
    return {"html": value, "kind": kind}


def communion_blocks():
    """The 1962 Communion starts at Ecce Agnus Dei; no second Confiteor.

    Emissa deliberately omits the entire popup. Preserve its remaining Latin
    text here, at the same position as &Communio_Populi in Ordo.txt.
    """
    source = (SOURCE / "web/www/missa/Latin/Ordo/Communio.txt").read_text()
    lines = source[source.index("S. Ecce Agnus Dei"):].splitlines()
    result = []
    for line in lines:
        if line.startswith("!"):
            value = f'<span class="ri">{html.escape(line[1:])}</span>'
        else:
            value = re.sub(r"^S\. ", '<span class="ri">S.</span> ', html.escape(line))
        if item := block(value):
            result.append(item)
    return result


def parse_rite(raw, kind):
    for error in ["cannot be opened", "Software error:", "missing!", "Can't open", "Undefined subroutine"]:
        if error in raw:
            raise ValueError(f"Incomplete {kind}: {error}")
    soup = BeautifulSoup(raw, "html.parser")
    headline = soup.select_one("p.cen > span")
    cells = soup.select("td[id]")
    if not headline or not cells:
        raise ValueError(f"No complete {kind} returned by the source renderer")
    title, _, rank = headline.get_text(" ", strip=True).partition(" ~ ")
    sections = []

    def start_section(label):
        section = {"id": f"s{len(sections) + 1}", "title": label, "blocks": []}
        sections.append(section)
        return section

    current = None
    communion_added = False
    last_gospel_added = False
    for cell in cells:
        paragraphs = cell.find_all("p", recursive=False) or [cell]
        for paragraph in paragraphs:
            # Split only at source line boundaries. Browser columns handle long
            # prose; no character counting or cut-off prayer approximations.
            fragments = re.split(r"<br\s*/?>", paragraph.decode_contents(), flags=re.I)
            for fragment in fragments:
                fragment = fragment.strip()
                if not plain(fragment):
                    continue
                parsed = BeautifulSoup(fragment, "html.parser")
                first = next((n for n in parsed.contents if str(n).strip()), None)
                if isinstance(first, Tag) and first.name == "b" and len(first.get_text().strip()) > 1:
                    label = first.get_text(" ", strip=True)
                    # Initials in liturgical texts are not section headings.
                    if label not in {"N.", "N. et N."} and not first.find_parent("span"):
                        current = start_section(label)
                        first.decompose()
                        fragment = str(parsed).strip()
                text = plain(fragment)
                if kind.startswith("Missa"):
                    if not communion_added and "Quod ore súmpsimus" in text:
                        previous_rubric = None
                        if current and current["blocks"] and current["blocks"][-1]["kind"] == "rubric":
                            previous_rubric = current["blocks"].pop()
                        current = start_section("Communio fidelium")
                        current["blocks"].extend(communion_blocks())
                        current = start_section("Ablutiones")
                        if previous_rubric:
                            current["blocks"].append(previous_rubric)
                        communion_added = True
                    if not last_gospel_added and "sacerdos in cornu Evangelii, iunctis manibus dicit" in text:
                        current = start_section("Ultimum Evangelium")
                        last_gospel_added = True
                    if text.startswith("Sanctus, Sanctus, Sanctus"):
                        current = start_section("Sanctus")
                if current is None:
                    current = start_section("Incipit")
                if item := block(fragment):
                    current["blocks"].append(item)
    sections = [s for s in sections if s["blocks"]]
    if sum(len(s["blocks"]) for s in sections) < 3:
        raise ValueError(f"Suspiciously short {kind}")
    return {"title": title, "rank": rank, "sections": sections}


def render_rite(day, kind, priest=False, missanumber=1, votive=None):
    query = {
        "version": SPEC["version"], "lang1": "Latin", "lang2": "Latin",
        "nofancychars": "0", "testmode": "regular",
    }
    if votive:
        query["votive"] = votive
    if kind.startswith("Missa"):
        script = SOURCE / "web/cgi-bin/missa/Emissa.pl"
        query |= {"date": day.strftime("%m-%d-%Y"), "first": "1", "rubrics": "1",
                  "solemn": "1" if kind == "Missa" else "0", "missanumber": str(missanumber)}
    else:
        script = SOURCE / "standalone/tools/epubgen2/EofficiumXhtml.pl"
        query |= {"date1": day.strftime("%m-%d-%Y"), "command": f"pray{kind}", "priest": "1" if priest else "0"}
    env = os.environ | {"PERL5LIB": str(SOURCE / "web/cgi-bin") + ":" + os.environ.get("PERL5LIB", "")}
    result = subprocess.run(
        ["perl", str(script), urlencode(query)], cwd=SOURCE / "standalone/tools/epubgen2",
        env=env, capture_output=True, text=True, encoding="utf-8", timeout=60, check=True,
    )
    if result.stderr.strip():
        raise ValueError(f"{day} {kind}: {result.stderr.strip()}")
    try:
        return parse_rite(result.stdout, kind)
    except ValueError as error:
        raise ValueError(f"{day} {kind} {votive or ''}: {error}") from error
