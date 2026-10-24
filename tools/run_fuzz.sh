#!/bin/sh
# Seeded fuzz differential: sqlite3GetToken vs the Come port over
# fragment-composed inputs (tools/gen_fuzz.py, fixed seed).
#
# 1. Generate tools/fuzz_corpus.h.
# 2. Build the C reference harness against it.
# 3. Record its token streams in tools/expected_fuzz.txt.
# 4. Regenerate src/tokenizer/t/06_fuzz_test.co.
# The generated test then runs as part of the normal suite.
set -e
cd "$(dirname "$0")/.."

python3 tools/gen_fuzz.py header
cc -O1 -DSQLITE_PRIVATE= -Itools -DCORPUS_H='"fuzz_corpus.h"' \
   tools/difftest.c tools/sqlite3.c -o tools/fuzzdiff -lpthread -lm
./tools/fuzzdiff > tools/expected_fuzz.txt
python3 tools/gen_fuzz.py come
echo "fuzz differential regenerated (seed in tools/gen_fuzz.py)"
