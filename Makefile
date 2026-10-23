COME ?= come

.PHONY: test demo diff
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
