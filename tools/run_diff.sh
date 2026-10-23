#!/bin/sh
# Differential test: SQLite's sqlite3GetToken vs the Come port.
#
# 1. Regenerate tools/corpus.h from tools/corpus.py.
# 2. Build the C reference harness (needs tools/sqlite3.c, the
#    SQLite amalgamation -- see tools/README.md).
# 3. Record its token streams in tools/expected.txt.
# 4. Regenerate t/04_differential_test.co with those expectations.
# The generated test then runs as part of `make test`.
set -e
cd "$(dirname "$0")/.."

python3 tools/corpus.py header
cc -O1 -DSQLITE_PRIVATE= -Itools tools/difftest.c tools/sqlite3.c \
   -o tools/difftest -lpthread -lm
./tools/difftest > tools/expected.txt
python3 tools/corpus.py come
echo "differential expectations regenerated from sqlite3GetToken"
