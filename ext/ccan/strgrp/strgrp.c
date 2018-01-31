/*
    Group similar strings
    Copyright (C) 2014  Andrew Jeffery <andrew@aj.id.au>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/
#include <assert.h>
#include <limits.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ccan/darray/darray.h"
#include "ccan/stringmap/stringmap.h"
#include "ccan/tal/tal.h"
#include "ccan/tal/str/str.h"
#include "strgrp.h"
#include "config.h"

#define CHAR_N_VALUES (1 << CHAR_BIT)

typedef darray(struct strgrp_grp *) darray_grp;
typedef darray(struct strgrp_item *) darray_item;

typedef stringmap(struct strgrp_grp *) stringmap_grp;

struct strgrp {
    double threshold;
    stringmap_grp known;
    unsigned int n_grps;
    darray_grp grps;
    int size;
    void (*score)(struct strgrp *const ctx, const char *const str);
};

struct strgrp_iter {
    const struct strgrp *ctx;
    int i;
};

struct strgrp_grp {
    const char *key;
    size_t key_len;
    darray_item items;
    ssize_t n_items;
    double score;

    /* Dynamic threshold bits */
    double threshold;
    double dirty;
};

struct strgrp_grp_iter {
    const struct strgrp_grp *grp;
    int i;
};

struct strgrp_item {
    const char *key;
    void *value;
};

/* Low-cost filter functions */

static inline bool
should_grp_score_len(const double threshold,
        const struct strgrp_grp *const grp, const char *const str) {
    const double lstr = (double) strlen(str);
    const double lkey = (double) grp->key_len;
    const double lmin = (lstr > lkey) ? lkey : lstr;
    const double s = sqrt((2 * lmin * lmin) / (1.0 * lstr * lstr + lkey * lkey));
    return threshold <= s;
}

/* Scoring - Longest Common Subsequence[2]
 *
 * [2] https://en.wikipedia.org/wiki/Longest_common_subsequence_problem
 */
#define ROWS 2

static inline int cmi(int i, int j) {
    return ROWS * j + i;
}

static inline int16_t
lcs(const char *const a, const char *const b) {
    const int lb = strlen(b);
    const int lbp1 = lb + 1;
    int16_t *const lookup = calloc(ROWS * lbp1, sizeof(int16_t));
    if (!lookup) {
        return -1;
    }
    int ia, ib;
    for (ia = (strlen(a) - 1); ia >= 0; ia--) {
        const char iav = a[ia];
        const int ial = (ia + 1) & 1; // ia last
        for (ib = lb - 1; ib >= 0; ib--) {
            const char ibv = b[ib];
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

#undef ROWS

static inline double
nlcs(const char *const a, const char *const b) {
    const double lcss = lcs(a, b);
    const double la = (double) strlen(a);
    const double lb = (double) strlen(b);
    const double s = sqrt((2 * lcss * lcss) / (la * la + lb * lb));
    return s;
}

static inline double
grp_score(const struct strgrp_grp *const grp, const char *const str) {
    return nlcs(grp->key, str);
}

/* Structure management */

static struct strgrp_item *
new_item(tal_t *const tctx, const char *const str, void *const data) {
    struct strgrp_item *i = talz(tctx, struct strgrp_item);
    if (!i) {
        return NULL;
    }
    i->key = tal_strdup(i, str);
    i->value = data;
    return i;
}

static bool
add_item(const struct strgrp *const ctx, struct strgrp_grp *const grp,
        const char *const str, void *const data) {
    struct strgrp_item *i = new_item(grp, str, data);
    if (!i) {
        return false;
    }
    darray_push(grp->items, i);
    grp->n_items++;
    grp->dirty = grp->n_items >= ctx->size;
    return true;
}

static void
free_grp(struct strgrp_grp *grp) {
    darray_free(grp->items);
}

static struct strgrp_grp *
new_grp(const struct strgrp *const ctx, const char *const str,
        void *const data) {
    struct strgrp_grp *b = talz(ctx, struct strgrp_grp);
    if (!b) {
        return NULL;
    }
    b->key = tal_strdup(b, str);
    b->key_len = strlen(str);
    b->n_items = 0;
    b->threshold = ctx->threshold;
    darray_init(b->items);
    tal_add_destructor(b, free_grp);
    if (!add_item(ctx, b, str, data)) {
        return tal_free(b);
    }
    return b;
}

static struct strgrp_grp *
add_grp(struct strgrp *const ctx, const char *const str,
        void *const data) {
    struct strgrp_grp *b = new_grp(ctx, str, data);
    if (!b) {
        return NULL;
    }
    darray_push(ctx->grps, b);
    ctx->n_grps++;
    return b;
}

static inline void
cache(struct strgrp *const ctx, struct strgrp_grp *const grp,
        const char *const str) {
    *(stringmap_enter(ctx->known, str)) = grp;
}

static void
grps_score(struct strgrp *const ctx, const char *const str) {
    int i;
// Keep ccanlint happy in reduced feature mode
#if HAVE_OPENMP
    #pragma omp parallel for schedule(dynamic)
#endif
    for (i = 0; i < ctx->n_grps; i++) {
        struct strgrp_grp *grp = darray_item(ctx->grps, i);
        grp->score = -1.0;
        if (should_grp_score_len(ctx->threshold, grp, str)) {
            grp->score = grp_score(grp, str) - ctx->threshold;
        }
    }
}

static void
grp_update_threshold(const struct strgrp *const ctx, struct strgrp_grp *grp) {
    double low = 1.0;
    ssize_t i;
    for (i = 0; i < grp->n_items; i++) {
        struct strgrp_item *a = darray_item(grp->items, i);
	int32_t j;
	for (j = i + 1; j < grp->n_items; j++) {
	    struct strgrp_item *b = darray_item(grp->items, j);
	    double score;
	    score = nlcs(a->key, b->key);
	    low = low < score ? low : score;
	}
    }

    /* Adjust low to capture extra variation */
    low -= 0.03;
    grp->threshold = low > ctx->threshold ? low : ctx->threshold;
}

static void
grps_score_dynamic(struct strgrp *const ctx, const char *const str) {
    int i;
// Keep ccanlint happy in reduced feature mode
#if HAVE_OPENMP
    #pragma omp parallel for schedule(dynamic)
#endif
    for (i = 0; i < ctx->n_grps; i++) {
        struct strgrp_grp *grp = darray_item(ctx->grps, i);
        grp->score = -2.0;
        if (grp->dirty) {
            grp_update_threshold(ctx, grp);
            grp->dirty = false;
        }
        if (should_grp_score_len(grp->threshold, grp, str)) {
            const double score = grp_score(grp, str);
            const double threshold = score >= grp->threshold ?
                ctx->threshold : grp->threshold;
            grp->score = score - threshold;
        }
    }
}

struct strgrp *
strgrp_new_dynamic(const double threshold, int size) {
    struct strgrp *ctx = talz(NULL, struct strgrp);
    ctx->threshold = threshold;
    ctx->size = size;
    ctx->score = size > 0 ? grps_score_dynamic : grps_score;
    stringmap_init(ctx->known, NULL);
    // n threads compare strings
    darray_init(ctx->grps);
    return ctx;
}

struct strgrp *
strgrp_new(const double threshold) {
    return strgrp_new_dynamic(threshold, 0);
}

static struct strgrp_grp *
grp_for(struct strgrp *const ctx, const char *const str) {
    int i;

    if (!ctx->n_grps) {
        return NULL;
    }
    {
        struct strgrp_grp **const grp = stringmap_lookup(ctx->known, str);
        if (grp) {
            return *grp;
        }
    }

    ctx->score(ctx, str);

    struct strgrp_grp *max = NULL;
    for (i = 0; i < ctx->n_grps; i++) {
        struct strgrp_grp *curr = darray_item(ctx->grps, i);

        if (!max || curr->score > max->score) {
            max = curr;
        }
    }
    return (max && max->score >= 0) ? max : NULL;
}

struct strgrp_grp *
strgrp_grp_for(struct strgrp *const ctx, const char *const str) {
    return grp_for(ctx, str);
}

struct strgrp_grp *
strgrp_grp_exact(struct strgrp *const ctx, const char *const str) {
    struct strgrp_grp **const grp = stringmap_lookup(ctx->known, str);
    if (!grp) {
        return NULL;
    }
    return *grp;
}

static bool score_gt(const struct strgrp_grp *a, const struct strgrp_grp *b) {
    return a->score > b->score;
}

static bool __score_gt(const void *a, const void *b) {
    return score_gt(a, b);
}

struct heap *
strgrp_grps_for(struct strgrp *const ctx, const char *const str) {
    int i;
    struct heap *heap;

    /* Sort descending */
    heap = heap_init(__score_gt);
    if (!heap) {
        perror("heap_init");
        return NULL;
    }

    if (!ctx->n_grps) {
        return heap;
    }

    ctx->score(ctx, str);

    for (i = 0; i < ctx->n_grps; i++) {
        struct strgrp_grp *curr = darray_item(ctx->grps, i);

        if (heap_push(heap, curr)) {
            perror("heap_push");
            heap_free(heap);
            return NULL;
        }
    }

    return heap;
}

bool
strgrp_grp_is_acceptible(const struct strgrp *ctx,
                         struct strgrp_grp *grp) {
    if (ctx->size > 0 && grp->dirty) {
        grp_update_threshold(ctx, grp);
        grp->dirty = false;
    }

    return grp->score >= 0;
}

ssize_t
strgrp_grp_size(const struct strgrp_grp *grp) {
    return grp->n_items;
}

struct strgrp_grp *
strgrp_grp_new(struct strgrp *ctx, const char *str, void *data) {
    struct strgrp_grp *pick = add_grp(ctx, str, data);
    if (pick) {
        cache(ctx, pick, str);
    }
    return pick;
}

bool
strgrp_grp_add(struct strgrp *ctx, struct strgrp_grp *grp, const char *str,
               void *data)
{
    if (!add_item(ctx, grp, str, data))
        return false;

    cache(ctx, grp, str);

    return true;
}

static struct strgrp_grp *
add(struct strgrp *const ctx, const char *const str, void *const data) {
    bool inserted = false;
    struct strgrp_grp *pick = grp_for(ctx, str);
    if (pick) {
        inserted = add_item(ctx, pick, str, data);
    } else {
        pick = add_grp(ctx, str, data);
        inserted = (NULL != pick);
    }
    if (inserted) {
        assert(NULL != pick);
        cache(ctx, pick, str);
    }
    return pick;
}

struct strgrp_grp *
strgrp_add(struct strgrp *const ctx, const char *const str, void *const data) {
    return add(ctx, str, data);
}

struct strgrp_iter *
strgrp_iter_new(struct strgrp *const ctx) {
    struct strgrp_iter *iter = talz(ctx, struct strgrp_iter);
    if (!iter) {
        return NULL;
    }
    iter->ctx = ctx;
    iter->i = 0;
    return iter;
}

struct strgrp_grp *
strgrp_iter_next(struct strgrp_iter *const iter) {
    return (iter->ctx->n_grps == iter->i) ?
        NULL : darray_item(iter->ctx->grps, iter->i++);
}

void
strgrp_iter_free(struct strgrp_iter *const iter) {
    tal_free(iter);
}

struct strgrp_grp_iter *
strgrp_grp_iter_new(const struct strgrp_grp *const grp) {
    struct strgrp_grp_iter *iter = talz(grp, struct strgrp_grp_iter);
    if (!iter) {
        return NULL;
    }
    iter->grp = grp;
    iter->i = 0;
    return iter;
}

const struct strgrp_item *
strgrp_grp_iter_next(struct strgrp_grp_iter *const iter) {
    return (iter->grp->n_items == iter->i) ?
        NULL : darray_item(iter->grp->items, iter->i++);
}

void
strgrp_grp_iter_free(struct strgrp_grp_iter *iter) {
    tal_free(iter);
}

const char *
strgrp_grp_key(const struct strgrp_grp *const grp) {
    return grp->key;
}

const char *
strgrp_item_key(const struct strgrp_item *const item) {
    return item->key;
}

void *
strgrp_item_value(const struct strgrp_item *const item) {
    return item->value;
}

void
strgrp_free(struct strgrp *const ctx) {
    darray_free(ctx->grps);
    stringmap_free(ctx->known);
    tal_free(ctx);
}

void
strgrp_free_cb(struct strgrp *const ctx, void (*cb)(void *data)) {
    struct strgrp_grp **grp;
    struct strgrp_item **item;
    darray_foreach(grp, ctx->grps) {
        darray_foreach(item, (*grp)->items) {
            cb((*item)->value);
        }
    }
    strgrp_free(ctx);
}

static void
print_item(const struct strgrp_item *item) {
    printf("\t%s\n", item->key);
}

static void
print_grp(const struct strgrp_grp *const grp) {
    struct strgrp_item **item;
    printf("%s:\n", grp->key);
    darray_foreach(item, grp->items) {
        print_item(*item);
    }
    printf("\n");
}

void
strgrp_print(const struct strgrp *const ctx) {
    struct strgrp_grp **grp;
    darray_foreach(grp, ctx->grps) {
        print_grp(*grp);
    }
}
