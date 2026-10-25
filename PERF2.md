# co_SQLite perf2 log (companion to come-lang PERF2.md)

Compiler steps (A lazy markers, B fat LTO) live in come-lang's
PERF2.md. This file logs the co_SQLite-side steps of the same
round, on branch `perf2` (from `redesign` 74bce7c).

Baselines for the co_SQLite steps are the post-B numbers
(perf2 compiler, redesign tokenizer with lookup_lower):
default faithful ~476, default fast ~346,
--lto faithful ~254, --lto fast ~253. Checksums for every
bench run: count=2,530,480 tokens, typesum=285119860,
lensum=7962360.

## Keyword hash port: sqlite3KeywordCode, literal (DONE)

New file src/tokenizer/keyword_hash.co: SQLite's keywordCode()
algorithm exactly — hash ((charMap(first)*4) ^ (charMap(last)*3)
^ len) % 127 with charMap(c) = c|32, 127 buckets, chains
(max 4, 36 buckets empty), length check first, then a
case-insensitive compare folding via (byte & 223) against
uppercase text, pre-reject len < 2 or len > 17. Tables
generated from sqlite-ref gen/keywordhash.h (buckets, chains,
lengths, offsets, 666-byte packed text) + keywords.co
(name -> TK_* code, matched by name; the two 147-keyword
sets are identical, verified by the generator). Chain order
is SQLite's (converted 1-based -> 0-based, 0 -> -1).

Two Come findings along the way (not bugs, language limits):
- Tuple returns cannot contain array types ((int[], byte[])
  fails to parse), so the builder is two functions
  (build_kw_tables(), build_kw_text()), not one.
- A bare assignment cannot infer an array type (kwt =
  build_kw_tables() fails); the callers declare int[]/byte[]
  explicitly.

Wiring: tk_scan/fast_scan now take (kwt, kwx) instead of the
kw map; cursor create() builds the tables once per instance;
stateless get_token/fast wrappers build per call (tests only,
not the bench). The map (tk_kw_map/tk_keyword_in/
keyword_code(string)) is KEPT for the stateless string API
(micro1 uses it); removing it is follow-up cleanup, not part
of this step. A miss now returns TK_ID without touching ERR
(the old lookup_lower path set ERR(ENOENT) on every miss).

New test 08_keywords_test.co: all 147 keywords in lower,
UPPER and alternating case via get_token (448 cases incl.
misses), plus cursor next()/fast_next() passes over all 147
in lower and alternating case (instance tables). The map is
already verified against C, so hash==map here transitively
verifies hash against C. (Test bug caught en route: next()
returns SPACE tokens too, so the cursor loops skip TK_SPACE.)

Measured 2026-10-24 (vs post-B; checksums exact, 8/8 suites):

| Build | Post-B | Keyword hash | Delta |
|---|---|---|---|
| Default faithful | ~476 | ~432 | -44 (-9%) |
| Default fast | ~346 | ~276 | -70 (-20%) |
| --lto faithful | ~254 | ~221 | -33 (-13%) |
| --lto fast | ~253 | ~157 | -96 (-38%) |

LTO fast needed a re-run: the first batch read 249/156/195
(VM noise); a 5-run batch is tight at 155-158, so ~157 is
the value. Gap to Go (131 ms) is now ~26 ms; to Rust
(80 ms) ~77 ms; to C (33 ms) ~124 ms.

## F: zero-copy bytes view (TRIED, NO WIN — no code change)

Checked open()'s ownership first, as planned. The bench
holds lines[] and one cursor for all 20 passes, so a view
of a line would be valid for the whole pass — but storing
it into tz_bytes (instance state) promotes by design:
come_string_byte_range() is documented as "the owned copy
of a byte range, used when a byte view reaches a storing
position and must promote", and field assignments adopt
to the destination's context (codegen). So
tz_bytes = sql.byte_view() would copy (view + promote),
the same ~8 ms as byte_array() (or slightly more). A
per-token view (no store) would be worse: 2.53M view
headers vs 80K line copies. No Come .byte_view() method
exists (only the C primitive), so F would also need a new
stdlib method for a ~8 ms ceiling that promotion erases.
Not pursued; a borrow-the-line cursor would be a language
ownership-model change, not a perf2 step.
- Cleanup (not perf): remove tk_kw_map/tk_keyword_in once
  keyword_code(string) is switched to the hash (his call,
  since keyword_code is public API).
- D (non-erroring map probe) is MOOT for the bench: the
  keyword port already removed the tokenizer's hot ERR-miss
  path, which was D's motivation. Do not do D for perf.

Compiler-side C (default -O2) is next, in come-lang.

## Follow-up: combined cursor method (branch next-token, from perf2)

Review #3 rank 1, tried on the user's "Sure" (2026-10-24).
Proposal: one call returning (type, len) instead of three
(next()/typ()/len()) per token.

Compiler gap found first: methods returning tuples do NOT
compile. The _ret_t typedef is emitted for plain functions
(get_token, tk_scan, fast_scan) but never for methods, so
any (int, int) method fails with "unknown type
come_tokenizer__next_token_ret_t". Come has no 3-tuples
either (only 2-tuples unpack). The clean tuple API is
therefore blocked on a compiler story of its own; it is
NOT fixed inside this trial.

Trial vehicle (measurement only): packed-int methods
next_token_packed() / fast_next_token_packed(), thin
wrappers over next()/fast_next() (state still set, so
typ()/len()/start() work after them). Packing: type in
bits 24-31, len in bits 0-23 (bench-valid: workload lines
< 1000 chars, so len < 2^24). End is packed
(TK_ILLEGAL, 0), decoded len 0. New test 09 verifies
packed == sequence in lockstep (type, len, start, end)
for 22 inputs, slow and fast; 9/9 suites green.
Benches switched to the packed methods (priming read +
while ((p & 16777215) != 0)).

Measured, INTERLEAVED old/new pairs (8 rounds each, same
VM phase; checksums exact throughout). Unpaired batches
overstated fast default by ~20 ms (phase drift), so the
paired numbers below are the honest ones:

| Build | Old (perf2) | Packed | Saving |
|---|---|---|---|
| Default faithful | ~327 | ~305 | ~22 ms |
| Default fast | ~222 | ~187 | ~35 ms |
| LTO faithful | ~221 | ~209 | ~15 ms |
| LTO fast | ~158 | ~141 | ~17 ms |

The LTO saving corrects review #3's audit: it is NOT
just call overhead (typ/len were already inlined under
LTO). The mechanism is the store-load round trip: the
old sequence stores tz_typ/tz_len to memory in next()
and loads them back in typ()/len(), and the compiler
keeps the round trip (tz is a heap pointer, aliasing
not provable). Packed returns both values in registers,
so the round trip disappears in both default and LTO.
That also explains why LTO saves ~15 ms for both
scanners (round-trip cost is scanner-independent).

Packed underestimates the clean tuple by the
encode+decode cost (~2 ns/token, ~5 ms total), so the
tuple estimate for LTO fast is ~136 ms (vs Go 131 ms,
~5 ms, noise-level). Faithful (the primary scanner)
remains ~70 ms behind Go even with the tuple, so
parity is NOT achieved for the product; only the trial
fast scanner approaches Go.

Status: branch next-token, tag perf2-next-token, NOT
merged. Two founder calls remain: (1) adopt the
combined method as public API (packed now, or tuple
after the compiler gap is fixed), and (2) the compiler
gap itself (method tuple _ret_t emission) as its own
story. Neither is decided by this trial.
