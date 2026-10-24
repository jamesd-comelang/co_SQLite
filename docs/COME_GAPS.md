# Come gaps found while porting SQLite's tokenizer

Everything below was hit against the real toolchain (Come v1.0.0
plus the post-v1.0 stories through COIL-140, repo HEAD `9d72c27`)
while doing this port, with a minimal repro for each. The port
invented no syntax and no APIs; where a gap forced a design change,
the change is listed under "Workaround used". Numbers are stable —
source comments and other docs refer to them.

**Update (2026-10-23, the COIL-141…149 fix pass):** the gaps were
reviewed with the language's author and fixed upstream, one story
each; the port was then finished against the new compiler
(come-lang HEAD `88eb3ca`). Each entry now carries a *Status:*
line. Three new gaps found during that finishing pass are #15–#17.
Still open: #3, #15, #16, #17.

## #1 — Cross-module constants are unreadable (spec §3.4)

`tokenizer.co` defines `const TK_SELECT = 139`, but an importer can
use neither `tokenizer.TK_SELECT` nor a bare `TK_SELECT` — the name
does not resolve across the module boundary.

*Workaround:* callers compare `tz.typ()` against
`tokenizer.token_name(t)` strings or the numeric values published
in `docs/TOKEN_MAP.md`. This is the single most limiting gap for a
port whose C original is built on shared `#define` constants: a
parser (step 2) will feel it everywhere.

*Status:* fixed as **COIL-148** — a constant belongs to its
module: one definition, visible to every file of the module, and
to importers through the export rule. The port's files now share
one TK_*/CC_* definition set. (Exporting all 186 constants to
importers hits the separate cap in #16, so `token_name()` and
the raw values remain the external comparison path.)

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

*Status:* fixed as **COIL-141** (a runtime misnaming: the
function was `come_string_to_byte_array`, codegen constructs
`come_string_byte_array`). The port now scans bytes exactly
like the C code; the codepoint machinery survives only inside
`token_text()`.

## #3 — `come test` cannot resolve a user project's own modules

`come test` discovers `.co` files under any `t/` directory but
builds each one from a fresh scratch working directory, and the
driver's `src/` module lookup anchors on that working directory —
so a test importing a project module never resolves, whether the
test sits in a top-level `t/` or in the module's own
`src/<module>/t/` (verified both ways, 2026-10-23). It works
inside Come's own repo only because those tests import system
modules from the depot. `come run src/tokenizer/t/x.co` from the
repo root resolves fine (the `src/` lookup anchors on the real
working directory there).

*Workaround:* `run_tests.sh` runs each suite with `come run` from
the repo root and treats the exit code as pass/fail.

*Status:* still open (re-verified 2026-10-23 against `88eb3ca`:
`come test .` fails identically). The workaround stands.

## #4 — No constant tables; a `map` literal is rebuilt per call

There is no way to build a lookup table once. `keyword_code(word)`
constructs the 147-entry `map{string,int}` on every call. Correct,
but a parser calling it per token pays for it.

*Status:* the table machinery is fixed as **COIL-142** —
module-level `map` declarations parse, singleton modules hold
bare-global tables, instance modules fill tables in `init()`.
The tokenizer still builds per call, because *sharing* a built
table across functions of a stateful module needs the map in a
function signature, which is #15.

## #5 — The single-quote character literal is unlexable

`'\''` and `'''` both fail to parse, so a `'` cannot be written as
a char literal.

*Workaround:* `const CP_SQUOTE = 39` and numeric comparisons.

*Status:* fixed as **COIL-143** (with #11): the char and string
scanners consume a backslash pair as a unit. `CP_SQUOTE` remains
as a named constant by choice, not necessity.

## #6 — Same-named constants in two files of one module collide at link

Constants are resolved per file and emitted as C globals. Two files
of the same directory module may each define `const TK_ID = 60`
and compile cleanly — the link then fails on duplicate symbols.

*Workaround:* per-file copies carry distinct names (`CH_*` in
`chars.co`, `KW_FALLBACK_ID` in `keywords.co`).

*Status:* fixed as **COIL-148** (with #1). The per-file copies
are gone: `chars.co` and `keywords.co` use tokenizer.co's
`CC_*` / `TK_ID` directly.

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

*Status:* fixed as **COIL-146** (with #9): tuple returns cross
module boundaries, destructures resolve through the registry.
The port's sub-scanners return tuples, the register variables
are deleted, and the public API is the originally planned
`get_token(sql, pos) -> (type, len)`. One wart remains in the
destructure path — see #17.

## #8 — WITHDRAWN (did not reproduce)

Originally filed as "a struct literal containing a function call
does not parse". Re-verified 2026-10-23 with a probe matrix —
plain calls, calls with arguments, designated initializers,
literals in return statements and as arguments, and cross-module
namespaced calls — and every form compiles and runs at Come HEAD
`9d72c27`. The port-time failure was almost certainly a
misattributed symptom of the parser capacity limit (#10), whose
spurious errors pointed at innocent lines in the oversized file.
Kept in the list, marked withdrawn, so the numbering other
documents cite stays stable.

## #9 — Struct values returned across a module boundary degrade

A consumer doing `var tok = mod.f()` then reading `tok.field`
fails with "not a structure", so struct-returning APIs do not
survive the module boundary in practice.

*Workaround (with #7):* the cursor API — `tokenizer.create()`,
`tz.open(sql)`, `tz.next()`, `tz.typ()/start()/len()/text()` —
carries token state inside the instance instead of returning
structs or tuples.

*Status:* fixed as **COIL-146** (with #7): importers receive
the exported struct definitions and exact prototypes.

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

*Status:* fixed as **COIL-147**: the token list grows with the
file instead of overflowing a fixed 4096 array into its own
count field (the wandering errors — and the silently dropped
constructs — were that overflow; this was also the true cause
behind the withdrawn #8). AST child appends go through a
checked path with a loud 1024-element limit. The four-file
split stays: it mirrors SQLite's own organization.

## #11 — String literals cannot contain `\"`

`"a\"b"` fails with "unterminated string literal", although the
language documentation lists `\"` as an escape. `\\` works; there
is no other way to put a `"` inside a string literal.

*Workaround:* build such strings with `sprintf("%c", '"')` and
concatenation (the test suites do this for double-quoted SQL).

*Status:* fixed as **COIL-143** (with #5). The test suites and
the differential generator now write `\"` directly.

## #12 — Lexer line-length limit (≈256 bytes)

A 317-character line containing one long string literal fails with
"unterminated string literal" — the lexer appears to truncate long
lines. Conditions and statements also cannot span lines.

*Workaround:* the generated differential test emits one short line
per token. *Operational note:* `come run`'s `.ccache` can go stale
on same-second edits; `rm -rf .ccache` before trusting a result.

*Status:* fixed as **COIL-144**: the lexer reads whole lines
into a growable buffer (was a fixed 256 bytes) and token text
is 4096 (was 128 — the char-130 corruption). A literal past the
limit is now a loud error.

## #13 — Array literals cannot be passed as call arguments

`f("x", {"TK_ID"}, {0}, {1})` reaches C as a bare `{...}` and fails
("expected expression before '{'"). Array literals work as
declaration initializers only.

*Workaround:* the test suites encode expectations as spec strings
("TK_SELECT:0:6 …") parsed by the harness functions.

*Status:* fixed as **COIL-145**: an array literal in expression
position materializes its header (statement expression) instead
of pasting raw braces into the C. (Founder ruled "allow", on the
strength of struct literals already being value expressions.)
The spec-string harness remains — as a notation, not a necessity.

## #14 — Stateful-module instances at module scope

`var tz = tokenizer.create()` as a module-level variable fails in
C ("initializer element is not constant"), and method dispatch on
a module-level instance variable mis-resolves — `.len()` compiled
to the string builtin `come_string_len`. Instances as locals and
as function parameters work correctly (COIL-140).

*Workaround:* create instances inside functions; pass them as
parameters (the differential test does exactly this).

*Ruling (2026-10-23, gap review):* instance creation belongs
inside functions only. The fix is a fence, not a feature: the
compiler should reject `create()` at module scope with a
Come-level error, instead of accepting the declaration and
failing in generated C.

*Status:* fixed in Come as **COIL-149** (come-lang `88eb3ca`):
the declaration-site codegen rejects it with "a module instance
can only be created inside a function…"; regression case
`tests/instance_project/bad_global.co` in come-lang.

## #15 — A map in a function signature breaks a stateful module

In a module with state (an instance module), a function whose
signature mentions a `map{...}` type — as a parameter or a return
value — is emitted into C with the Come map syntax untranslated:
the defining file's own generated C contains
`map{string, int} come_<mod>__build(void);` and fails to compile.
The identical functions compile and run in a stateless module.

*Minimal repro:* a two-file module with one module variable, a
`map{string,int} build()` helper, and an exported
`int lookup(string)` that uses it. Add the module variable (make
the module stateful) and the build breaks; remove it and the
same code works.

*Consequence for this port:* the COIL-142 build-once table
pattern cannot be shared across the tokenizer's functions —
a table passed as a parameter or returned from a builder is
exactly the shape that breaks — so `keyword_code()` keeps its
per-call local map (a local map in no signature is fine).

## #16 — The export surface silently caps at 64 symbols

A module may export at most 64 symbols. Beyond that, the excess
exports silently vanish: importers see "not exported" (Come
level) or undeclared `come_<mod>__const_*` identifiers in the
generated C. No diagnostic names the cap.

*Measured 2026-10-23:* a synthetic module exporting N constants
plus one function works for N = 63 (64 symbols total) and fails
for N = 64 (65 total), the last constant missing from the
importer. The cap counts all exported symbols together.

*Consequence for this port:* the 186 TK_* constants cannot be
exported (the module already exports 12 functions). Callers
keep comparing `token_name()` strings or the raw values in
`docs/TOKEN_MAP.md` — the #1 workaround, retained for this
reason only.

## #17 — Tuple-call destructuring emits string literals raw

`(t, n) = mod.get_token("SELECT 1", 0)` — destructuring a
tuple-returning cross-module call — emits the string-literal
argument as a raw C `char*` instead of a `come_string_t`, and
the C compile fails with "incompatible type for argument 1".
The same call with a string *variable* argument works, and
scalar-returning calls convert literals correctly; only the
tuple-destructure call path skips the conversion.

*Workaround:* bind literals to a variable first
(`string stmt = "SELECT 1"`), as test 01 does.

---

## Readiness assessment

After the COIL-141…149 pass, the port reads the way it was
designed to: the scanner works on bytes like the C code (#2),
sub-scanners return tuples and the public API is
`get_token(sql, pos) -> (type, len)` (#7/#9), one constant
definition serves the whole module (#1/#6), literals and long
lines behave (#11/#12/#13), and file size is no longer a cliff
(#10). What remains open is narrower: test discovery (#3), map
types in signatures of stateful modules (#15), the 64-symbol
export cap (#16), and a literal-conversion wart in the tuple
call path (#17). For step 2 (the parser), #16 is the one that
will bite first: a parser module wants to import the token
constants by name.
