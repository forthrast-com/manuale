.PHONY: source data fonts build serve test

source:
	python3 tools/fetch_source.py

data: source
	python3 tools/generate.py

# The reading faces are derived from IM FELL English and checked in; rerun
# only after changing tools/patch_fonts.py. Every table is reproducible.
fonts:
	python3 tools/patch_fonts.py

build:
	python3 tools/build.py

serve: build
	python3 -m http.server 4173 --bind 127.0.0.1 --directory dist

test:
	python3 -m unittest discover -s tests -v
	node --test tests/*.test.mjs
