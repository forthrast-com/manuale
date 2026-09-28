"""Derive the reading faces from IM FELL English, adding the accents it lacks.

The corpus writes sǽcula and cælum's kin with ǽ 5,846 times, and obœ́diens
with a combining acute on œ 139 times. FELL has neither glyph, so a browser
drew those letters, or whole clusters, from a system serif mid-word. The text
is right and stays untouched; the font learns to set it.

Added, all as composites of FELL's own outlines:
- ǽ and Ǽ, placed as FELL places the acute on its other vowels;
- a combining acute, so a base and its mark stay in one face;
- a ccmp ligature from vowel + combining acute to the composed glyph, for
  shapers that do not compose on their own; œ́ has no code point, so this is
  the only way it gets one glyph.

The licence reserves the name IM FELL English, so the result is renamed.
Run with fontTools after changing this file; the outputs are checked in.
"""

from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphComponent

ROOT = Path(__file__).resolve().parents[1]
FACES = [("im_fell_english.ttf", "manuale_fell.ttf", "Regular"),
         ("im_fell_english_italic.ttf", "manuale_fell_italic.ttf", "Italic")]
FAMILY = "Manuale Fell"
COMBINING_ACUTE = 0x0301
# FELL's own composed vowels, from which the accent's lean is measured.
LOWER = {"a": "aacute", "e": "eacute", "o": "oacute", "u": "uacute"}
UPPER = {"A": "Aacute", "E": "Eacute", "O": "Oacute", "U": "Uacute"}
# Base + U+0301 → composed glyph, for the ccmp ligature.
PRECOMPOSED = {"a": "aacute", "e": "eacute", "i": "iacute", "o": "oacute", "u": "uacute",
               "y": "yacute", "A": "Aacute", "E": "Eacute", "I": "Iacute", "O": "Oacute",
               "U": "Uacute", "Y": "Yacute", "ae": "aeacute", "oe": "oeacute",
               "AE": "AEacute", "OE": "OEacute"}


def centre(font, name):
    glyph = font["glyf"][name]
    glyph.recalcBounds(font["glyf"])
    return (glyph.xMin + glyph.xMax) / 2


def lean(font, pairs, accent):
    """How far right of the base's centre FELL sets this accent, on average."""
    offsets = []
    for base, composed in pairs.items():
        shift = next(c.x for c in font["glyf"][composed].components if c.glyphName == accent)
        offsets.append(centre(font, accent) + shift - centre(font, base))
    return sum(offsets) / len(offsets)


def composite(font, name, parts, advance, lsb=None):
    glyph = Glyph()
    glyph.components = []
    for part, x in parts:
        component = GlyphComponent()
        component.glyphName, component.x, component.y, component.flags = part, round(x), 0, 0
        glyph.components.append(component)
    glyph.numberOfContours = -1
    font["glyf"][name] = glyph
    glyph.recalcBounds(font["glyf"])
    font["hmtx"][name] = (advance, glyph.xMin if lsb is None else lsb)
    if name not in font.getGlyphOrder():
        font.setGlyphOrder(font.getGlyphOrder() + [name])


def accented(font, base, accent, skew):
    return [(base, 0), (accent, centre(font, base) + skew - centre(font, accent))]


def add_ccmp(font, ligatures):
    gsub = font["GSUB"].table
    subst = otTables.LigatureSubst()
    subst.ligatures = {}
    for (base, mark), result in sorted(ligatures.items()):
        ligature = otTables.Ligature()
        ligature.LigGlyph, ligature.Component = result, [mark]
        ligature.CompCount = 2
        subst.ligatures.setdefault(base, []).append(ligature)
    lookup = otTables.Lookup()
    lookup.LookupType, lookup.LookupFlag, lookup.SubTable = 4, 0, [subst]
    lookup.SubTableCount = 1
    gsub.LookupList.Lookup.append(lookup)
    gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
    feature = otTables.Feature()
    feature.FeatureParams, feature.LookupListIndex = None, [len(gsub.LookupList.Lookup) - 1]
    feature.LookupCount = 1
    record = otTables.FeatureRecord()
    record.FeatureTag, record.Feature = "ccmp", feature
    records = gsub.FeatureList.FeatureRecord
    records.append(record)
    index = len(records) - 1
    for script in gsub.ScriptList.ScriptRecord:
        systems = [script.Script.DefaultLangSys] + [r.LangSys for r in script.Script.LangSysRecord]
        for system in filter(None, systems):
            system.FeatureIndex.append(index)
            system.FeatureCount = len(system.FeatureIndex)
    # Feature records must stay sorted by tag; remap every reference.
    order = sorted(range(len(records)), key=lambda i: records[i].FeatureTag)
    remap = {old: new for new, old in enumerate(order)}
    gsub.FeatureList.FeatureRecord = [records[i] for i in order]
    for script in gsub.ScriptList.ScriptRecord:
        systems = [script.Script.DefaultLangSys] + [r.LangSys for r in script.Script.LangSysRecord]
        for system in filter(None, systems):
            system.FeatureIndex = sorted(remap[i] for i in system.FeatureIndex)


def rename(font, style):
    full = FAMILY if style == "Regular" else f"{FAMILY} {style}"
    names = {1: FAMILY, 2: style, 3: f"{FAMILY} {style}; derived from IM FELL English",
             4: full, 6: full.replace(" ", "-")}
    table = font["name"]
    for record in list(table.names):
        if record.nameID in {16, 17, 18, 21, 22}:
            table.removeNames(nameID=record.nameID)
    for name_id, value in names.items():
        table.setName(value, name_id, 3, 1, 0x409)
        table.setName(value, name_id, 1, 0, 0)
    copyright = table.getDebugName(0)
    table.setName(f"{copyright}. Modified for Manuale: accented æ, Æ, œ, Œ and a combining acute added.", 0, 3, 1, 0x409)


def patch(source, target, style):
    font = TTFont(ROOT / "tools/fonts" / source)
    small, capital = lean(font, LOWER, "acute"), lean(font, UPPER, "Acute")
    for name, base, accent, skew in [("aeacute", "ae", "acute", small), ("oeacute", "oe", "acute", small),
                                     ("AEacute", "AE", "Acute", capital), ("OEacute", "OE", "Acute", capital)]:
        composite(font, name, accented(font, base, accent, skew), font["hmtx"][base][0])
    # Zero-width, and drawn to sit over the preceding lowercase letter for any
    # shaper that neither composes nor positions marks itself.
    width = font["hmtx"]["e"][0]
    composite(font, "acutecomb", [("acute", centre(font, "e") + small - width - centre(font, "acute"))], 0)
    for table in font["cmap"].tables:
        if table.isUnicode():
            table.cmap.update({0x01FD: "aeacute", 0x01FC: "AEacute", COMBINING_ACUTE: "acutecomb"})
    add_ccmp(font, {(base, "acutecomb"): result for base, result in PRECOMPOSED.items()})
    rename(font, style)
    font["maxp"].recalc(font)
    font.save(ROOT / "src/fonts" / target)


if __name__ == "__main__":
    for face in FACES:
        patch(*face)
        print(f"src/fonts/{face[1]}")
