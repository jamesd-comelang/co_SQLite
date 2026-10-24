#!/bin/sh
# Run every .co test suite in src/tokenizer/t/ and report a summary.
# Uses `come run` from the repo root: `come test` builds each test
# in isolation and cannot resolve the project's src/ modules from
# src/tokenizer/t/ (docs/COME_GAPS.md #3).
set -u
cd "$(dirname "$0")"
COME=${COME:-come}
command -v "$COME" >/dev/null 2>&1 || COME=../come-lang/build/come
fail=0
for t in src/tokenizer/t/*_test.co; do
    rm -rf .ccache
    if "$COME" run "$t"; then
        echo "ok: $t"
    else
        echo "FAILED: $t"
        fail=1
    fi
done
if [ "$fail" = 0 ]; then echo "ALL TESTS PASSED"; else echo "SOME TESTS FAILED"; fi
exit $fail
