"""The reading faces set every letter of the text in one face.

A letter the face lacks is drawn from a system serif instead, and a browser
keeps a base letter and its combining mark in one font, so a missing accent
takes its letter with it. That is how sǽcula and obœ́diens came to look broken.
"""

from functools import cache
import gzip
import json
from pathlib import Path
import re
import sys
import tempfile
import unicodedata
import unittest

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import patch_fonts

READING = ["manuale_fell.ttf", "manuale_fell_italic.ttf"]
DISPLAY = "fraunces.ttf"
# Liturgical signs no bundled face draws; the system's serif supplies them.
BORROWED = set("℣℟✠✙")
# Invisible, default-ignorable characters: nothing to draw.
IGNORABLE = {"​", "︎", "️"}


@cache
def face(name):
    return TTFont(ROOT / "src/fonts" / name)


def described(characters):
    return sorted(f"U+{ord(c):04X} {unicodedata.name(c, '?')}" for c in characters)


@cache
def published():
    """Every character, heading character and mark sequence the calendar prints.

    Reads the packs as text rather than parsing them: the JSON and its markup
    are ASCII, so the letters are all that is left to check.
    """
    index = json.loads((ROOT / "data/index.json").read_text())
    letters, headings, sequences = set(), set(), set()
    for day in index["days"]:
        raw = gzip.decompress((ROOT / f"data/days/{day}.json.gz").read_bytes()).decode()
        letters |= set(raw)
        for heading in re.findall(r'"(?:title|rank)":"((?:[^"\\]|\\.)*)"', raw):
            headings |= set(heading)
        sequences |= set(re.findall(r"[^̀-ͯ][̀-ͯ]+", raw))
    return frozenset(letters), frozenset(headings), frozenset(sequences)


def ligatures(font, feature):
    result = {}
    gsub = font["GSUB"].table
    for record in gsub.FeatureList.FeatureRecord:
        if record.FeatureTag != feature:
            continue
        for index in record.Feature.LookupListIndex:
            for table in gsub.LookupList.Lookup[index].SubTable:
                for first, entries in getattr(table, "ligatures", {}).items():
                    for entry in entries:
                        result[(first, *entry.Component)] = entry.LigGlyph
    return result


class ReadingFaceTests(unittest.TestCase):
    def test_every_published_letter_is_in_both_reading_faces(self):
        letters, _, _ = published()
        # Everything but control characters, so spaces of every width count.
        needed = {c for c in letters if unicodedata.category(c) != "Cc"} - BORROWED - IGNORABLE
        for name in READING:
            with self.subTest(face=name):
                missing = {c for c in needed if ord(c) not in face(name).getBestCmap()}
                self.assertEqual(described(missing), [])

    def test_every_accented_letter_becomes_one_glyph(self):
        _, _, sequences = published()
        self.assertTrue(sequences, "the corpus stopped using combining marks; is this test still needed?")
        for name in READING:
            font = face(name)
            cmap, joined = font.getBestCmap(), ligatures(font, "ccmp")
            for sequence in sequences:
                with self.subTest(face=name, sequence=sequence):
                    composed = unicodedata.normalize("NFC", sequence)
                    if len(composed) == 1 and ord(composed) in cmap:
                        continue
                    glyphs = tuple(cmap.get(ord(c)) for c in sequence)
                    self.assertIn(glyphs, joined, described(sequence))

    def test_headings_are_in_the_display_face(self):
        _, headings, _ = published()
        cmap = face(DISPLAY).getBestCmap()
        missing = {c for c in headings if ord(c) not in cmap} - BORROWED - IGNORABLE
        self.assertEqual(described(missing), [])


class DerivedFaceTests(unittest.TestCase):
    def test_the_patch_reproduces_the_bundled_faces(self):
        with tempfile.TemporaryDirectory() as directory:
            for source, target, style in patch_fonts.FACES:
                patch_fonts.patch(source, target, style, output=Path(directory))
                with self.subTest(face=target):
                    self.assertEqual((Path(directory) / target).read_bytes(),
                                     (ROOT / "src/fonts" / target).read_bytes(),
                                     "rerun tools/patch_fonts.py and commit the result")

    def test_the_documented_upstream_faces_are_the_ones_bundled(self):
        documented = set(re.findall(r"`([0-9a-f]{40})`", (ROOT / "src/fonts/README.md").read_text()))
        originals = [ROOT / "tools/fonts" / source for source, _, _ in patch_fonts.FACES]
        actual = {patch_fonts.git_blob(path) for path in originals + [ROOT / "src/fonts" / DISPLAY]}
        self.assertEqual(documented, actual)
        self.assertEqual({patch_fonts.git_blob(path) for path in originals}, set(patch_fonts.UPSTREAM.values()))

    def test_the_reserved_name_is_not_used(self):
        # The licence lets the outlines be modified but reserves the name.
        for _, target, _ in patch_fonts.FACES:
            names = face(target)["name"]
            for name_id in (1, 3, 4, 6, 16, 17):
                value = names.getDebugName(name_id) or ""
                with self.subTest(face=target, name_id=name_id):
                    self.assertFalse(value.startswith("IM FELL") or value.startswith("IM_FELL"), value)

    def test_new_glyphs_kern_like_their_bases(self):
        kerned = 0
        for _, target, _ in patch_fonts.FACES:
            pairs = face(target)["kern"].kernTables[0].kernTable
            for accented, (base, _, _) in patch_fonts.ACCENTED.items():
                with self.subTest(face=target, glyph=accented):
                    for side in (0, 1):
                        partners = {pair[1 - side] for pair in pairs if pair[side] == base}
                        self.assertEqual(partners, {pair[1 - side] for pair in pairs if pair[side] == accented})
                        kerned += len(partners)
        # FELL never kerns œ, but it kerns æ and Æ on both sides.
        self.assertGreater(kerned, 0)

    def test_only_the_derived_faces_ship(self):
        stylesheet = (ROOT / "src/styles.css").read_text()
        page = (ROOT / "src/index.html").read_text()
        referenced = set(re.findall(r"\./fonts/([\w.-]+\.ttf)", stylesheet + page))
        bundled = {path.name for path in (ROOT / "src/fonts").glob("*.ttf")}
        self.assertEqual(referenced, bundled)
        self.assertEqual(bundled, {target for _, target, _ in patch_fonts.FACES} | {DISPLAY})


if __name__ == "__main__":
    unittest.main()
