from datetime import date
import tempfile
from functools import cache
import gzip
import hashlib
import json
import re
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from liturgy import HOURS, SPEC, parse_rite, sanitise, plain, render_rite


def normal(value):
    return "".join(c for c in unicodedata.normalize("NFD", value) if not unicodedata.combining(c)).lower()


@cache
def load_day(day):
    return json.loads(gzip.decompress((ROOT / f"data/days/{day}.json.gz").read_bytes()))


@cache
def load_rite(day, kind="Missa"):
    # Fixed regression dates must still run after the published years roll
    # forward. Render only the required fixture instead of publishing it.
    if (ROOT / f"data/days/{day}.json.gz").exists():
        return load_day(day)["rites"][kind]
    mass = re.fullmatch(r"(MissaLecta|Missa)([23])?(?:-(\w+))?", kind)
    if mass:
        return render_rite(date.fromisoformat(day), mass[1], missanumber=int(mass[2] or 1), votive=mass[3] or "")
    return render_rite(date.fromisoformat(day), kind.removesuffix("Choro"), priest=kind.endswith("Choro"))


def text(rite, spoken_only=False):
    return normal(" ".join(plain(block["html"]) for section in rite["sections"] for block in section["blocks"] if not spoken_only or block["kind"] != "rubric"))


class ImportBoundaryTests(unittest.TestCase):
    def test_fixed_regression_dates_work_outside_published_years(self):
        with patch(__name__ + ".ROOT", ROOT / "scratch/absent_fixture_directory"):
            mass = load_rite.__wrapped__("2026-09-06", "Missa")
            vespers = load_rite.__wrapped__("2026-09-06", "VesperaChoro")
        self.assertIn("XV Post Pentecosten", mass["title"])
        self.assertIn("dominus vobiscum", text(vespers))

    def test_error_page_cannot_become_a_prayer(self):
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            parse_rite('<p>Evangelium missing!</p>', "Missa")

    def test_navigation_only_export_fails(self):
        with self.assertRaises(ValueError):
            parse_rite('<p class="cen"><span>Dominica</span></p>', "Vespera")

    def test_html_boundary_removes_executable_content(self):
        result = sanitise('<script>alert(1)</script><span onclick="evil()" style="color:red" class="ri unknown">Orémus.</span><a href="javascript:evil()">Amen.</a><img src=x onerror="evil()">')
        self.assertEqual(result, '<span class="rubric">Orémus.</span>Amen.')

    def test_response_markers_are_not_hidden_as_rubrics(self):
        result = sanitise('<span class="ri">℟.</span> Amen.')
        self.assertIn('class="versicle"', result)
        self.assertNotIn('class="rubric"', result)

    def test_corpus_has_every_declared_rite_and_valid_hashes(self):
        index = json.loads((ROOT / "data/index.json").read_text())
        required = {"Missa", "MissaLecta", *HOURS, *(f"{hour}Choro" for hour in HOURS)}
        required |= {f"{kind}-{code}" for kind in ["Missa", "MissaLecta"] for code in index["votives"]}
        self.assertGreaterEqual(len(index["days"]), 365)
        for day, metadata in index["days"].items():
            with self.subTest(day=day):
                packed = (ROOT / f"data/days/{day}.json.gz").read_bytes()
                self.assertEqual(hashlib.sha256(packed).hexdigest(), metadata["sha256"])
                payload = json.loads(gzip.decompress(packed))
                self.assertEqual(payload["date"], day)
                self.assertTrue(required <= payload["rites"].keys())
                for rite in payload["rites"].values():
                    self.assertTrue(rite["title"])
                    self.assertTrue(rite["sections"])
                    ids = [section["id"] for section in rite["sections"]]
                    self.assertEqual(len(ids), len(set(ids)))
                    self.assertNotIn("missing!", json.dumps(rite))


class IndexBuildingTests(unittest.TestCase):
    def _index(self, packs):
        import generate
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "days").mkdir()
            for day, payload in packs.items():
                (output / "days" / f"{day}.json.gz").write_bytes(
                    gzip.compress(json.dumps(payload).encode(), mtime=0))
            with patch.object(generate, "OUTPUT", output):
                generate.write_index()
                return json.loads((output / "index.json").read_text())

    def _pack(self, day, **overrides):
        import generate
        payload = {"schema": generate.SCHEMA, "date": day, "source": SPEC["revision"],
                   "generator": generate.GENERATOR,
                   "rites": {"Missa": {"title": "Test", "rank": "IV. classis", "sections": []}}}
        return payload | overrides

    def test_packs_from_an_older_pin_are_skipped_not_fatal(self):
        # A restored artifact, or a year rolling forward, leaves these behind.
        index = self._index({
            "2026-01-01": self._pack("2026-01-01"),
            "2025-01-01": self._pack("2025-01-01", generator="an older importer", source="older"),
        })
        self.assertEqual(sorted(index["days"]), ["2026-01-01"])

    def test_a_pack_contradicting_its_own_generator_is_fatal(self):
        with self.assertRaisesRegex(ValueError, "contradicts its own generator"):
            self._index({"2026-01-01": self._pack("2026-01-01", source="something else")})


class OrdinaryDerivationTests(unittest.TestCase):
    """The ordinary is derived from recurrence, not from a list of incipits."""

    def _rite(self, *texts):
        return {"title": "T", "rank": "IV. classis",
                "sections": [{"id": "s1", "title": "Introitus",
                              "blocks": [{"html": x, "kind": "prayer"} for x in texts]}]}

    def test_what_recurs_is_ordinary_and_what_varies_is_not(self):
        import generate
        days = [{"rites": {"Missa": self._rite("Dominus vobiscum.", f"Proper of day {n}")}}
                for n in range(10)]
        ordinary = set(generate.ordinary_ids(days))
        self.assertIn(generate.block_id("Dominus vobiscum."), ordinary)
        self.assertNotIn(generate.block_id("Proper of day 3"), ordinary)

    def test_votive_propers_are_not_counted_as_ordinary(self):
        # A votive repeats its own proper daily; counting it would erase it.
        import generate
        days = [{"rites": {"Missa": self._rite(f"Proper of day {n}"),
                           "Missa-C11": self._rite("Salve, sancta parens")}} for n in range(10)]
        self.assertNotIn(generate.block_id("Salve, sancta parens"),
                         set(generate.ordinary_ids(days)))

    def test_markup_and_spacing_do_not_change_a_block_id(self):
        import generate
        bare = generate.block_id("Orémus.")
        self.assertEqual(generate.block_id('<span class="rubric">Orémus.</span>'), bare)
        self.assertEqual(generate.block_id("<b>Orémus.</b>   "), bare)
        self.assertNotEqual(generate.block_id("Oremus."), bare)

    def test_the_published_index_separates_the_two(self):
        index = json.loads((ROOT / "data/index.json").read_text())
        ordinary = set(index["ordinary"])
        day = load_day("2026-09-06")["rites"]["Missa"]
        blocks = {b["html"]: s["title"] for s in day["sections"] for b in s["blocks"]}
        import generate
        def marked(needle):
            match = next(h for h in blocks if needle in generate.block_text(h))
            return generate.block_id(match) in ordinary
        # The deacon's preparation sits inside Evangelium; the Gospel does not.
        self.assertTrue(marked("Munda cor meum"))
        self.assertTrue(marked("Súscipe, sancte Pater"))
        self.assertFalse(marked("Ibat Iesus in civitátem"))
        self.assertFalse(marked("Exspéctans exspectávi"))


class SpecialRiteTests(unittest.TestCase):
    def test_only_the_holy_week_rites_lack_an_introit(self):
        """The app uses the Introit to tell a Mass from a rite of its own.

        If that ever stopped being exact, the propers view would quietly hand
        back a fragment of Good Friday instead of refusing.
        """
        index = json.loads((ROOT / "data/index.json").read_text())
        without = set()
        for day in index["days"]:
            payload = load_day(day)
            for kind in ("Missa", "MissaLecta"):
                rite = payload["rites"][kind]
                if not any(s["title"] == "Introitus" for s in rite["sections"]):
                    without.add(rite["title"])
        self.assertEqual(without, {"Feria Sexta in Passione et Morte Domini", "Sabbato Sancto"})


class CalendarAndFlowTests(unittest.TestCase):
    def test_sundays_after_pentecost_and_their_readings(self):
        # XIV Post Pentecosten on 30 August 2026 agrees with a published
        # 1962-Missal calendar; see docs/sources.md. The readings are from
        # the source corpus, not from that comparison.
        august = load_rite("2026-08-30")
        september = load_rite("2026-09-06")
        self.assertIn("XIV Post Pentecosten", august["title"])
        self.assertIn("XV Post Pentecosten", september["title"])
        self.assertIn("gal 5:16-24", text(august))
        self.assertIn("matt 6:24-33", text(august))
        self.assertIn("luc 7:11-16", text(september))

    def test_prophets_and_canon_stay_in_order(self):
        rite = load_rite("2026-08-30")
        titles = [section["title"] for section in rite["sections"]]
        order = ["Introitus", "Lectio", "Evangelium", "Offertorium", "Secreta", "Præfatio", "Sanctus", "Canon", "Communio fidelium", "Ablutiones", "Communio", "Postcommunio", "Ultimum Evangelium"]
        self.assertEqual(sorted(titles.index(title) for title in order), [titles.index(title) for title in order])
        communion = next(section for section in rite["sections"] if section["title"] == "Communio fidelium")
        value = text({"sections": [communion]})
        self.assertIn("ecce agnus dei", value)
        self.assertEqual(value.count("domine, non sum dignus"), 3)
        self.assertNotIn("confiteor", value)
        self.assertIn("hoc est enim corpus meum", text(rite))
        self.assertIn("hic est enim calix sanguinis mei", text(rite))

    def test_penitential_omissions(self):
        rite = load_rite("2026-03-22", "MissaLecta")
        spoken = text(rite, spoken_only=True)
        # The same words occur in this Sunday's Introit: only the altar
        # prayers omit Psalm 42, not every occurrence throughout the Mass.
        preparation = []
        for section in rite["sections"]:
            if section["title"] == "Introitus":
                break
            preparation.append(section)
        self.assertNotIn("iudica me, deus", text({"sections": preparation}, spoken_only=True))
        self.assertIn("iudica me, deus", spoken)
        self.assertNotIn("gloria in excelsis deo", spoken)

    def test_rosary_gospel_is_resolved(self):
        rite = load_rite("2026-10-07")
        self.assertIn("missus est angelus gabriel", text(rite))

    def test_vespers_and_matins_are_complete(self):
        rites = {kind: load_rite("2026-08-30", kind) for kind in ["Vespera", "VesperaChoro", "Matutinum"]}
        self.assertIn("magnificat", text(rites["Vespera"]))
        self.assertIn("benedicamus domino", text(rites["Vespera"]))
        self.assertGreater(len(text(rites["Matutinum"])), 8000)
        self.assertIn("dominus vobiscum", text(rites["VesperaChoro"]))
        self.assertNotIn("dominus vobiscum", text(rites["Vespera"]))

    def test_votive_changes_whole_mass_not_office(self):
        rites = {kind: load_rite("2026-09-06", kind) for kind in ["Missa", "Missa-C9", "Missa-C11", "Laudes"]}
        self.assertIn("requiem", text(rites["Missa-C9"]))
        self.assertNotIn("gloria in excelsis deo", text(rites["Missa-C9"], spoken_only=True))
        self.assertIn("XV Post Pentecosten", rites["Laudes"]["title"])
        self.assertNotEqual(rites["Missa"]["title"], rites["Missa-C11"]["title"])

    def test_three_christmas_masses(self):
        rites = {kind: load_rite("2026-12-25", kind) for kind in ["Missa", "Missa2", "Missa3", "MissaLecta2", "MissaLecta3"]}
        self.assertTrue({"Missa", "Missa2", "Missa3", "MissaLecta2", "MissaLecta3"} <= rites.keys())
        self.assertNotEqual(text(rites["Missa"]), text(rites["Missa2"]))
        self.assertNotEqual(text(rites["Missa2"]), text(rites["Missa3"]))


if __name__ == "__main__":
    unittest.main()
