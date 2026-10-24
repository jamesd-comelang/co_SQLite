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
| 6b | Coverage parity with the pure C original: SQLite's own `test/tokenize.test` (14 cases) ported at token level (suite 05); seeded fragment-fuzz differential vs C (suite 06, 400 inputs) as the breadth the TCL suite gives the C tokenizer | ✅ |
| 7 | Docs: behavior matrix, Come gaps, provenance; assessment of Come readiness | ✅ |

### Dependency mapping (SQLite → Come), from tasklet 0

| SQLite (C) dependency | Come equivalent | Verdict |
|---|---|---|
| `const unsigned char *z` byte string, NUL-terminated | `string.byte_array()` → `byte[]`, scanned directly | ✅ (fixed COIL-141; embedded NUL / invalid UTF-8 remain impossible in a Come string — see BEHAVIOR.md) |
| `aiClass[256]` byte class table | `tk_class(c)` if-chain over bytes (identical table; 0xEF → CC_BOM, ≥0x80 → CC_ID) | ✅ |
| `sqlite3CtypeMap` (Isspace/Isdigit/Isxdigit/IdChar) | small predicate functions on bytes | ✅ |
| `keywordhash.h` perfect hash | `map{string,int}` lookup on the lowercased word | ✅ (slower; rebuilt per call — a shared build-once table is blocked by COME_GAPS #15) |
| `parse.h` TK_* `#define`s | `const` group in `tokenizer.co`, shared by the module's files | ✅ inside the module (COIL-148); exporting all 186 hits the 64-symbol cap (COME_GAPS #16) |
| returning (type, length) via out-param + return | tuple return `(int, int)` | ✅ (fixed COIL-146) — the public API is `get_token(sql, pos) -> (type, len)`; the cursor remains for streaming |
| `sqlite3Isspace` etc. macros | plain functions | ✅ |
| parser-state reclassification of WINDOW/OVER/FILTER (`sqlite3RunParser`) | **out of scope**: lives in the parser driver, not `sqlite3GetToken`; raw codes returned (TK_WINDOW/TK_OVER/TK_FILTER), reclassification documented for step 2 | ⛔ by design |

### Blockers found before implementation (tasklet 0)

1. `string.byte_array()` — the documented way to get raw bytes —
   did not compile (COME_GAPS #2); the first version of the port
   therefore scanned by codepoint. **Resolved by COIL-141**; the
   port was finished on bytes (see "Finishing pass" below).
2. Cross-module constants were unreadable (§3.4). **Resolved
   inside the module by COIL-148**; exporting all 186 constants
   to importers hits the 64-symbol cap (COME_GAPS #16), so
   `token_name()` + TOKEN_MAP.md remain the external path.
3. `come test` builds each test in isolation and cannot resolve a
   project module from `src/tokenizer/t/` → tests run through `run_tests.sh`
   (`come run` from the repo root, where the `src/` rule applies).
   **Still open** (COME_GAPS #3).

## Later steps (backlog, not started)

- Step 2: Lemon grammar → parser driver, incl. the WINDOW/OVER/FILTER
  and TK_SPACE/TK_COMMENT handling that lives in `sqlite3RunParser`.
- Step 3: `sqlite3Dequote*`, token → Expr values (numbers/strings).
- Each later step starts with its own tasklet breakdown like this one.

## Finishing pass (2026-10-23, against Come `88eb3ca`)

The gap review turned each tokenizer gap into a Come story
(COIL-141…149). With those landed, the port was finished the way
it was originally designed:

- Scanner works on **bytes** (`byte_array()`, COIL-141) — a direct
  transliteration of `tokenize.c`; the codepoint conversion layer
  survives only inside `token_text()`.
- Sub-scanners **return tuples**; the module-register variables
  are deleted (COIL-146). Public API gains the C-shaped
  `get_token(sql, byte_pos) -> (type, len)`; the cursor stays.
- **One constant definition** serves all four files (COIL-148);
  the `CH_*` / `KW_FALLBACK_ID` per-file copies are gone.
- Tests write `\"` and `\'` plainly (COIL-143); the
  differential generator dropped its `sprintf` quote plumbing.
- The cursor converts the input to bytes once, in `open()`.

Re-verified end to end: all four suites green, the 123-case
differential re-run against the C harness with identical
expectations. Three narrower gaps were found by this pass and
filed as COME_GAPS #15–#17 (maps in signatures of stateful
modules, the 64-symbol export cap, literal arguments on the
tuple-destructure path).

## Assessment (step 1)

Come was sufficient for a byte-exact tokenizer with **zero invented
syntax**: the port is a four-file directory module using strings,
byte arrays, one map and consts, verified token-for-token against
the C original on 123 differential inputs plus three hand-written
suites. The friction was never in the scanner itself but at the
seams — and after the fix pass the seams that remain are test
discovery (#3), map-typed signatures in stateful modules (#15),
the export cap (#16) and the tuple-call literal wart (#17). For
step 2, #16 is the one to watch: a parser wants the token
constants by name. Full assessment: docs/COME_GAPS.md.
