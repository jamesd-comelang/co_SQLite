COME ?= come

.PHONY: test demo diff fuzz
test:
	./run_tests.sh

demo:
	$(COME) run examples/demo.co

# Regenerate the differential expectations from SQLite's own
# tokenizer (needs tools/sqlite3.c; see tools/README.md), then run
# the full suite including the regenerated differential test.
diff:
	./tools/run_diff.sh
	./run_tests.sh

# Regenerate the seeded fuzz differential (fragment-composed
# inputs, tools/gen_fuzz.py) from SQLite's sqlite3GetToken,
# then run the full suite including the regenerated fuzz test.
fuzz:
	./tools/run_fuzz.sh
	./run_tests.sh
