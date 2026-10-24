/* C benchmark: sqlite3GetToken over workload.sql, line by line.
 * Same work as bench.co: read all lines once, then N passes of
 * full tokenization, accumulating a checksum (token count, type
 * sum, length sum) so the loop cannot be optimized away. The
 * checksum must match the Come bench exactly.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

long long sqlite3GetToken(const unsigned char *z, int *tokenType);

#define MAX_LINES 8192
#define PASSES 20

int main(void) {
    FILE *f = fopen("workload.sql", "r");
    if (!f) { fprintf(stderr, "cannot open workload.sql\n"); return 1; }
    static char buf[8192];
    char *lines[MAX_LINES];
    int nlines = 0;
    while (fgets(buf, sizeof buf, f) && nlines < MAX_LINES) {
        size_t n = strlen(buf);
        while (n && (buf[n - 1] == '\n' || buf[n - 1] == '\r')) buf[--n] = 0;
        lines[nlines] = malloc(n + 1);
        memcpy(lines[nlines], buf, n + 1);
        nlines++;
    }
    fclose(f);

    long long count = 0, tsum = 0, lsum = 0;
    for (int pass = 0; pass < PASSES; pass++) {
        for (int i = 0; i < nlines; i++) {
            const unsigned char *z = (const unsigned char *)lines[i];
            long long pos = 0, n;
            int t;
            for (;;) {
                n = sqlite3GetToken(z + pos, &t);
                if (n == 0) break;
                count++;
                tsum += t;
                lsum += n;
                pos += n;
            }
        }
    }
    printf("C: %lld tokens, typesum=%lld lensum=%lld (%d passes, %d lines)\n",
           count, tsum, lsum, PASSES, nlines);
    return 0;
}
