# tools/

## gen_token_data.py — token data generator

Two modes:

```sh
# 1. Extract from a SQLite source tree (needs the tree's own
#    generators already run: gen/parse.h via tool/lemon.c on
#    src/parse.y, gen/keywordhash.h via tool/mkkeywordhash.c):
python3 tools/gen_token_data.py --extract /path/to/sqlite-tree
#    -> writes tools/token_data.json

# 2. Generate (default): splice the TK_* constants, keyword map
#    and token-name table into the .co sources and rewrite
#    docs/TOKEN_MAP.md:
python3 tools/gen_token_data.py
```

The spliced regions are fenced by `// <generated …>` markers in
`src/tokenizer/tokenizer.co`, `src/tokenizer/keywords.co` and
`src/tokenizer/names.co`. Do not edit inside the fences by hand.

## corpus.py + difftest.c + run_diff.sh — differential test

`corpus.py` holds the single source of truth for the differential
corpus (123 SQL inputs). `run_diff.sh`:

1. regenerates `tools/corpus.h` from the corpus (C string literals,
   octal-escaped — C `\x` escapes are greedy and would corrupt
   bytes followed by hex characters),
2. builds `tools/difftest.c` against the SQLite amalgamation,
3. records SQLite's own token streams in `tools/expected.txt`,
4. regenerates `src/tokenizer/t/04_differential_test.co` with those expectations
   (numeric type/start/length triples, one short line per token —
   Come's lexer has a line-length limit, see COME_GAPS #12).

The amalgamation is **not** committed. Fetch it once:

```sh
curl -O https://www.sqlite.org/2025/sqlite-amalgamation-3500400.zip
unzip sqlite-amalgamation-3500400.zip
cp sqlite-amalgamation-3500400/sqlite3.c tools/sqlite3.c
```

`difftest.c` calls the internal `sqlite3GetToken`; the amalgamation
exposes it when compiled with `-DSQLITE_PRIVATE=` (the declaration
sits behind `#ifndef SQLITE_PRIVATE`). This is a test harness
against SQLite's own source, not use of a public API — SQLite does
not export a stable tokenizer API.
