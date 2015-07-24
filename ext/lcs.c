#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include "lcs.h"

#define ROWS 2

static inline int cmi(int i, int j) {
    return ROWS * j + i;
}

int16_t
lcs(const char * const a, const char * const b) {
    const int lb = strlen(b);
    const int lbp1 = lb + 1;
    int16_t * const lookup = calloc(ROWS * lbp1, sizeof(int16_t));
    if (!lookup) {
        return -1;
    }
    int ia, ib;
    for (ia = (strlen(a) - 1); ia >= 0; ia--) {
        const char iav = a[ia];
        for (ib = lb - 1; ib >= 0; ib--) {
            const char ibv = b[ib];
            const int ial = (ia + 1) & 1; // ia last
            const int iac = ia & 1; // ia current
            const int ibl = ib + 1; // ib last
            // don't need separate "ib current" as it's just ib
            if (iav == ibv) {
                lookup[cmi(iac, ib)] = 1 + lookup[cmi(ial, ibl)];
            } else {
                const int16_t valb = lookup[cmi(ial, ib)];
                const int16_t vabl = lookup[cmi(iac, ibl)];
                lookup[cmi(iac, ib)] = (valb > vabl) ? valb : vabl;
            }
        }
    }
    int16_t result = lookup[0];
    free(lookup);
    return result;
}
