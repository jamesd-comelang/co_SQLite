# co_SQLite

**SQLite, rewritten in [Come](https://github.com/jamesd-comelang/come-lang) — one component at a time.**

This project ports SQLite to the Come programming language in small,
independently verifiable steps ("tasklets"). It doubles as a field test
of Come on real-world systems code: every place Come cannot yet express
what the C original does is recorded in
[docs/COME_GAPS.md](docs/COME_GAPS.md), not worked around silently.

SQLite is in the public domain (see [docs/PROVENANCE.md](docs/PROVENANCE.md)).

## Status

| Step | Component | Status |
|-----:|-----------|--------|
| 1 | SQL tokenizer (`src/tokenize.c` → `src/tokenizer/`) | ✅ done — see below |
| 2+ | Parser, VDBE, storage … | not started |

## Step 1: the SQL tokenizer

`src/tokenizer/` is a faithful port of SQLite's `sqlite3GetToken()`
(`src/tokenize.c` in the SQLite tree, trunk @ `f879fb1`) plus
`sqlite3KeywordCode()` (generated `keywordhash.h`). It classifies and
measures tokens exactly like SQLite — including the quirks:
`X'AB'` blobs, `?NNN`/`:name`/`$tcl(...)` variables, `--` and `/* */`
comments, digit separators (`1_000` → `TK_QNUMBER`), `->`/`->>`,
unterminated quotes → `TK_ILLEGAL`, a UTF-8 BOM read as `TK_SPACE`,
and numbers that absorb trailing identifier characters as `TK_ILLEGAL`.

### API (module `tokenizer`)

A cursor over the input, plus stateless helpers:

```come
import tokenizer

var tz = tokenizer.create()          // a tokenizer cursor instance
tz.open(sql)                         // start scanning sql
while (tz.next()) {                  // advance; false at end of input
    int t    = tz.typ()              // TK_* code (SQLite's values)
    int pos  = tz.start()            // byte offset of the token
    int n    = tz.len()              // byte length of the token
    string s = tz.text()             // the token's text (a slice view)
}
tz.destroy()

int    tokenizer.token_type_at(sql, byte_pos)  // one-shot: type at a byte offset
int    tokenizer.token_len_at(sql, byte_pos)   // one-shot: byte length there
string tokenizer.token_text(sql, start, len)   // slice of the input
int    tokenizer.keyword_code(word)            // TK_* or TK_ID
string tokenizer.token_name(type)              // "TK_SELECT", "" if unknown
```

The cursor mirrors how SQLite's parser drives `sqlite3GetToken()`:
each step yields a token type and a **byte length** into the
original input. Nothing is allocated per token — token text is
always `sql` sliced by (byte offset, byte length), and
`token_type_at`/`token_len_at` expose the same one-shot shape as
the C function for callers that track positions themselves.

At end of input `next()` simply returns false; positionally,
`token_type_at` at the end returns `TK_ILLEGAL` with length 0,
exactly like `sqlite3GetToken()` on the terminating NUL — the
parser layer above it (step 2, not part of this tasklet) is what
turns that into `TK_SEMI`/EOF.

Token type constants (`TK_SELECT`, …) are defined in
`src/tokenizer/tokenizer.co` with the exact numeric values from
SQLite's generated `parse.h`, and listed in
[docs/TOKEN_MAP.md](docs/TOKEN_MAP.md). **Come limitation:**
constants cannot yet be read from another module (Come spec §3.4
gap), so callers compare against the raw values from the map or
`tokenizer.token_name(t)` — see docs/COME_GAPS.md #1. The cursor
shape itself is also gap-driven: tuple and struct returns do not
survive module boundaries (COME_GAPS #7, #9).

### Build & test

Needs the Come toolchain (`come` on PATH, or set `COME=/path/to/come`).

```sh
make test        # .co test suites in src/tokenizer/t/ (exit code = pass/fail)
make demo        # tokenize a sample statement and print the tokens
make diff        # differential test vs the real sqlite3GetToken (C)
```

`make diff` downloads nothing: it expects a SQLite amalgamation at
`tools/sqlite3.c` (see `tools/README.md`) and compiles the reference
harness in `tools/difftest.c` against it.

## Layout

```
src/tokenizer/       the tokenizer (only deliverable of step 1):
                     tokenizer.co (scanner + API), chars.co (char
                     classes), keywords.co (keyword table),
                     names.co (token names)
src/tokenizer/t/     .co test suites (run via run_tests.sh, see COME_GAPS #3)
examples/demo.co     small driver that prints a token stream
docs/                PROJECT.md (tasklets), TOKEN_MAP.md, BEHAVIOR.md,
                     COME_GAPS.md, PROVENANCE.md
tools/               token-data generator + C differential harness
```

## Project docs

- [docs/PROJECT.md](docs/PROJECT.md) — the agile tasklet plan and its history.
- [docs/TOKEN_MAP.md](docs/TOKEN_MAP.md) — every SQLite token value, and
  the keyword → token-code table (generated from SQLite sources).
- [docs/BEHAVIOR.md](docs/BEHAVIOR.md) — supported / unsupported lexical
  behavior, and every known divergence from the C tokenizer.
- [docs/COME_GAPS.md](docs/COME_GAPS.md) — Come language/stdlib limits found.
- [docs/PROVENANCE.md](docs/PROVENANCE.md) — sources, versions, licensing.
