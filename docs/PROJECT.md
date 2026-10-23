# Project plan — co_SQLite

SQLite rewritten in Come, agile-style: a backlog of small tasklets,
each finished, tested and committed before the next one starts.
A tasklet is "done" only when its tests actually ran green with the
real Come toolchain.

## Step 1 — SQL tokenizer (this step)

Reference: SQLite trunk `f879fb1` (2026-10-21), `src/tokenize.c`
(`sqlite3GetToken`, `sqlite3RunParser` excluded), `src/parse.y`
(token values via `tool/lemon.c`), `tool/mkkeywordhash.c`
(keyword list), `sqlite3CtypeMap` (character classes).

| # | Tasklet | Status |
|--:|---------|--------|
| 0 | Recon: read Come spec/stdlib; read SQLite tokenizer + deps; map deps → Come capabilities; log blockers | ✅ |
| 1 | Token types: generate TK_* constants + keyword table from SQLite sources; token map doc; API skeleton compiles | ✅ |
| 2 | Core scanner: whitespace, BOM, EOF, single/double-char operators & punctuation | ✅ |
| 3 | Identifiers & keywords; quoted identifiers (`"…"`, `` `…` ``, `[…]`) | ✅ |
| 4 | Literals: `'strings'`, `X'blobs'`, integers/floats/exponents/hex, digit separators (`TK_QNUMBER`) | ✅ |
| 5 | Bind parameters (`?`, `?NNN`, `:n`, `@n`, `$n`, `$n(...)`, `#n`, `::`); `TK_ILLEGAL` paths; unterminated constructs | ✅ |
| 6 | Test suites in Come (`t/`), differential harness vs C `sqlite3GetToken`; regression tests for every divergence found | ✅ |
| 7 | Docs: behavior matrix, Come gaps, provenance; assessment of Come readiness | ✅ |

### Dependency mapping (SQLite → Come), from tasklet 0

| SQLite (C) dependency | Come equivalent | Verdict |
|---|---|---|
| `const unsigned char *z` byte string, NUL-terminated | `string` (immutable, UTF-8, character-first) + byte offsets recomputed from codepoints | ⚠️ works for valid UTF-8; embedded NUL / invalid UTF-8 impossible — see BEHAVIOR.md |
| `aiClass[256]` byte class table | `class_of(cp)` if-chain over codepoints (ASCII table identical; ≥0x80 → CC_ID) | ✅ |
| `sqlite3CtypeMap` (Isspace/Isdigit/Isxdigit/IdChar) | small predicate functions on codepoints | ✅ |
| `keywordhash.h` perfect hash | `map{string,int}` lookup on the lowercased word | ✅ (slower; rebuilt per call — COME_GAPS #4) |
| `parse.h` TK_* `#define`s | `const` group in `tokenizer.co` | ⚠️ usable inside the module only (COME_GAPS #1) |
| returning (type, length) via out-param + return | tuple return `(int, int)` | ⛔ tuples do not survive module boundaries (COME_GAPS #7) — internal scanners report through module registers; the public API is a cursor (COME_GAPS #9) |
| `sqlite3Isspace` etc. macros | plain functions | ✅ |
| parser-state reclassification of WINDOW/OVER/FILTER (`sqlite3RunParser`) | **out of scope**: lives in the parser driver, not `sqlite3GetToken`; raw codes returned (TK_WINDOW/TK_OVER/TK_FILTER), reclassification documented for step 2 | ⛔ by design |

### Blockers found before implementation (tasklet 0)

1. `string.byte_array()` — the documented way to get raw bytes —
   does not compile (returns `int` to codegen; COME_GAPS #2). The
   tokenizer therefore scans by **codepoint** and converts to byte
   offsets via UTF-8 length — exact for valid UTF-8 input.
2. Cross-module constants are unreadable (§3.4) → API works around it
   with `token_name()`; numeric values published in TOKEN_MAP.md.
3. `come test` builds each test in isolation and cannot resolve a
   project module from `t/` → tests run through `run_tests.sh`
   (`come run` from the repo root, where the `src/` rule applies).

None of these blocked the port; all three are logged with repros in
COME_GAPS.md.

## Later steps (backlog, not started)

- Step 2: Lemon grammar → parser driver, incl. the WINDOW/OVER/FILTER
  and TK_SPACE/TK_COMMENT handling that lives in `sqlite3RunParser`.
- Step 3: `sqlite3Dequote*`, token → Expr values (numbers/strings).
- Each later step starts with its own tasklet breakdown like this one.

## Assessment (step 1)

Come was sufficient for a byte-exact tokenizer with **zero invented
syntax**: the port is a four-file directory module using strings,
one map and consts, verified token-for-token against the C
original on 123 differential inputs plus three hand-written suites.
The friction was not in the scanner itself but at the seams —
raw-byte access, cross-module constants, tuple/struct returns
across module boundaries, file-size and line-length limits, and
test discovery (COME_GAPS #1–#14). A parser (step 2) will stress
exactly those seams harder (shared token constants, struct-heavy
AST), so gaps #1 and #2, in that order, are what most limits
porting the next component. Full assessment: docs/COME_GAPS.md.
