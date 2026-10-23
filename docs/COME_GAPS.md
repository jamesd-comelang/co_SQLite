# Come gaps found while porting SQLite's tokenizer

Everything below was hit against the real toolchain (Come v1.0.0
plus the post-v1.0 stories through COIL-140, repo HEAD `9d72c27`)
while doing this port, with a minimal repro for each. The port
invented no syntax and no APIs; where a gap forced a design change,
the change is listed under "Workaround used". Numbers are stable —
source comments and other docs refer to them.

## #1 — Cross-module constants are unreadable (spec §3.4)

`tokenizer.co` defines `const TK_SELECT = 139`, but an importer can
use neither `tokenizer.TK_SELECT` nor a bare `TK_SELECT` — the name
does not resolve across the module boundary.

*Workaround:* callers compare `tz.typ()` against
`tokenizer.token_name(t)` strings or the numeric values published
in `docs/TOKEN_MAP.md`. This is the single most limiting gap for a
port whose C original is built on shared `#define` constants: a
parser (step 2) will feel it everywhere.

## #2 — `string.byte_array()` does not compile

The documented raw-byte accessor fails in codegen (its result is
treated as `int`), so there is currently no working way to read a
string's bytes.

*Workaround:* the tokenizer scans by **codepoint**
(`sql[i]` → wchar) and converts character offsets to byte offsets
with UTF-8 lengths. Exact for valid UTF-8; invalid UTF-8 and
embedded NUL are unrepresentable in Come strings, so SQLite's
byte-level behavior for those inputs cannot be ported
(`docs/BEHAVIOR.md`).

## #3 — `come test` cannot resolve project modules from `t/`

`come test` builds each test in isolation; a test in `t/` that
imports a project module from `src/` does not resolve, while
`come run t/x.co` from the repo root does (the `src/` lookup rule
applies there).

*Workaround:* `run_tests.sh` runs each suite with `come run` from
the repo root and treats the exit code as pass/fail.

## #4 — No constant tables; a `map` literal is rebuilt per call

There is no way to build a lookup table once. `keyword_code(word)`
constructs the 147-entry `map{string,int}` on every call. Correct,
but a parser calling it per token pays for it.

## #5 — The single-quote character literal is unlexable

`'\''` and `'''` both fail to parse, so a `'` cannot be written as
a char literal.

*Workaround:* `const CP_SQUOTE = 39` and numeric comparisons.

## #6 — Same-named constants in two files of one module collide at link

Constants are resolved per file and emitted as C globals. Two files
of the same directory module may each define `const TK_ID = 60`
and compile cleanly — the link then fails on duplicate symbols.

*Workaround:* per-file copies carry distinct names (`CH_*` in
`chars.co`, `KW_FALLBACK_ID` in `keywords.co`).

## #7 — Tuple returns are unusable across file/module boundaries

Several compounding problems: destructuring `(a, b) = f()` is
rejected for cross-module calls; generated importer prototypes for
tuple-returning functions of a stateful module reference undefined
`*_ret_t` types; `return f()` where `f` returns a tuple counts as
returning one value; destructuring only declares new names at a
function's top level.

*Workaround:* the tokenizer's internal sub-scanners report through
module "register" variables, and the public API exposes only
scalar returns and a cursor object. The originally planned API —
a `get_token(sql, pos) -> (type, len)` mirroring the C function —
had to be abandoned for this reason (see #9 as well).

## #8 — A struct literal containing a function call does not parse

`struct Token{T, pos, tk_byte_len(...)}` is rejected by the parser.

## #9 — Struct values returned across a module boundary degrade

A consumer doing `var tok = mod.f()` then reading `tok.field`
fails with "not a structure", so struct-returning APIs do not
survive the module boundary in practice.

*Workaround (with #7):* the cursor API — `tokenizer.create()`,
`tz.open(sql)`, `tz.next()`, `tz.typ()/start()/len()/text()` —
carries token state inside the instance instead of returning
structs or tuples.

## #10 — Parser capacity limit on large files

A single large `.co` file fails with spurious "unexpected
top-level token" errors. Synthetic boundary: 26 functions × 15
one-line `if`s fails; 25 × 15 passes; one function × 400 `if`s
passes. The largest `.co` file in Come's own repo is 368 lines —
the limit sits in a range real code reaches quickly (SQLite's
`tokenize.c` alone would exceed it).

*Workaround:* the tokenizer is a directory module split across
four files (`tokenizer.co`, `chars.co`, `keywords.co`,
`names.co`).

## #11 — String literals cannot contain `\"`

`"a\"b"` fails with "unterminated string literal", although the
language documentation lists `\"` as an escape. `\\` works; there
is no other way to put a `"` inside a string literal.

*Workaround:* build such strings with `sprintf("%c", '"')` and
concatenation (the test suites do this for double-quoted SQL).

## #12 — Lexer line-length limit (≈256 bytes)

A 317-character line containing one long string literal fails with
"unterminated string literal" — the lexer appears to truncate long
lines. Conditions and statements also cannot span lines.

*Workaround:* the generated differential test emits one short line
per token. *Operational note:* `come run`'s `.ccache` can go stale
on same-second edits; `rm -rf .ccache` before trusting a result.

## #13 — Array literals cannot be passed as call arguments

`f("x", {"TK_ID"}, {0}, {1})` reaches C as a bare `{...}` and fails
("expected expression before '{'"). Array literals work as
declaration initializers only.

*Workaround:* the test suites encode expectations as spec strings
("TK_SELECT:0:6 …") parsed by the harness functions.

## #14 — Stateful-module instances at module scope

`var tz = tokenizer.create()` as a module-level variable fails in
C ("initializer element is not constant"), and method dispatch on
a module-level instance variable mis-resolves — `.len()` compiled
to the string builtin `come_string_len`. Instances as locals and
as function parameters work correctly (COIL-140).

*Workaround:* create instances inside functions; pass them as
parameters (the differential test does exactly this).

---

## Readiness assessment

The scanner itself ported cleanly: control flow, character
classification, the keyword table and all of SQLite's quirks are
expressible in Come today, byte-exact, with no invented syntax.
Every workaround above lives at a **boundary** — bytes vs
characters (#2), module borders (#1, #6, #7, #9, #14), file size
(#10, #12), and test discovery (#3). Those boundaries are exactly
what the next SQLite components stress harder: a parser needs
shared token constants everywhere (#1), an AST wants structs in
arrays and maps (#8/#9 family), and the C sources are far larger
than one Come file (#10). Fixing #1 and #2 first would remove the
most friction per unit of work for step 2.
