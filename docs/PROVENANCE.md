# Provenance and licensing

## SQLite sources

SQLite is in the public domain (https://sqlite.org/copyright.html);
its authors dedicate it to the public benefit with no warranty.
This port preserves attribution anyway, because the mapping to the
original is the project's audit trail.

Reference tree: a clone of https://github.com/sqlite/sqlite at
trunk commit `f879fb1` (2026-10-21). Files that informed the port:

| SQLite file | What was taken |
|---|---|
| `src/tokenize.c` | `sqlite3GetToken` — the behavioral reference for every scanning rule; `aiClass[]` character classes |
| `src/parse.y` via `tool/lemon.c` | token names and numeric values (generated `parse.h`, 186 `TK_*` defines) |
| `tool/mkkeywordhash.c` | the keyword list (147 keywords in a default build; WITHIN gated out) and its hashing preconditions (first-char and length rules) |
| `src/global.h` / `src/sqliteInt.h` | `sqlite3CtypeMap` semantics (`IdChar`: letters, digits, `_`, `$`, ≥ 0x80) |
| amalgamation **3.50.4** (`sqlite3.c`) | differential harness only: compiled with `-DSQLITE_PRIVATE=` so the test program can call the internal `sqlite3GetToken`; its token values were checked against the trunk anchors above |

The `.co` implementation is an original re-expression of that
behavior in Come, written for this repository; the generated
artifacts (`tools/token_data.json`, `docs/TOKEN_MAP.md`, the
constant block in `src/tokenizer/tokenizer.co`, the keyword table in
`src/tokenizer/keywords.co`, and the name table in
`src/tokenizer/names.co`) are produced from the SQLite sources by
`tools/gen_token_data.py` and are marked as generated in place.

## This repository

Original work in this repository (the Come code, tests, harness
drivers and documentation) is by the repository author. SQLite's
public-domain dedication covers the ported behavior and the
generated tables derived from its sources.
