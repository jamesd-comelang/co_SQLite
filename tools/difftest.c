/*
** difftest.c -- reference harness for the differential test.
**
** Links against the SQLite amalgamation (tools/sqlite3.c) compiled
** with -DSQLITE_PRIVATE= so the internal sqlite3GetToken() is
** visible, and prints, for every corpus input in corpus.h, the
** token stream as "type,start,len" triples, one case per line:
**
**   case <i>: t,s,l t,s,l ...
**
** The terminating (TK_ILLEGAL, 0) is not printed. Compare with the
** Come implementation via tools/run_diff.sh.
*/
#include <stdio.h>
#include <string.h>

long long sqlite3GetToken(const unsigned char *z, int *tokenType);

#include "corpus.h"

int main(void){
  int i, t;
  for(i=0; i<N_CASES; i++){
    const unsigned char *z = (const unsigned char*)cases[i];
    long long pos = 0, n;
    printf("case %d:", i);
    for(;;){
      n = sqlite3GetToken(z + pos, &t);
      if( n==0 ) break;
      printf(" %d,%lld,%lld", t, pos, n);
      pos += n;
    }
    printf("\n");
  }
  return 0;
}
