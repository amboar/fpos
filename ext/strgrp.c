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
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/
#include <stdbool.h>
#include <string.h>
#include "ccan/talloc/talloc.h"
#include "ccan/list/list.h"
#include "ccan/htable/htable.h"
#include "ccan/hash/hash.h"
#include "strgrp.h"
#include "lcs.h"

struct strgrp {
    double threshold;
    struct htable known;
    struct list_head bins;
    unsigned int n_bins;
};

struct strgrp_iter {
    struct list_head *head;
    struct strgrp_bin *current;
};

struct strgrp_bin {
    char * key;
    size_t key_len;
    int32_t n_items;
    struct list_node list;
    struct list_head items;
};

struct strgrp_bin_iter {
    struct list_head *head;
    struct strgrp_item *current;
};

struct strgrp_item {
    char * key;
    void * value;
    struct list_node list;
};

struct strgrp_map {
    char * key;
    struct strgrp_bin * bin;
};

static inline double
nlcs(const char * const a, const char * const b) {
    const double lcss = lcs(a, b);
    return 2 * lcss / (strlen(a) + strlen(b));
}

static bool
should_bin_score(const struct strgrp * const ctx, const struct strgrp_bin * const bin,
        const char * const str) {
    const size_t strl = strlen(str);
    const size_t keyl = bin->key_len;
    double sr =  strl / keyl;
    if (1 < sr) {
        sr = 1 / sr;
    }
    return ctx->threshold <= sr;
}

static inline double
bin_score(const struct strgrp_bin * const ctx, const char * const str) {
    return nlcs(ctx->key, str);
}

static struct strgrp_item *
new_item(TALLOC_CTX * const tctx, const char * const str, void * const data) {
    struct strgrp_item * i = talloc_zero(tctx, struct strgrp_item);
    if (!i) {
        return NULL;
    }
    i->key = talloc_strdup(i, str);
    i->value = data;
    return i;
}

static bool
add_item(struct strgrp_bin * const ctx, const char * const str,
        void * const data) {
    struct strgrp_item * i = new_item(ctx, str, data);
    if (!i) {
        return false;
    }
    list_add(&ctx->items, &i->list);
    ctx->n_items++;
    return true;
}

static struct strgrp_bin *
new_bin(TALLOC_CTX * const tctx, const char * const str, void * const data) {
    struct strgrp_bin * b = talloc_zero(tctx, struct strgrp_bin);
    if (!b) {
        return NULL;
    }
    b->key = talloc_strdup(b, str);
    b->key_len = strlen(str);
    b->n_items = 0;
    list_head_init(&b->items);
    if (!add_item(b, str, data)) {
        talloc_free(b);
        return NULL;
    }
    return b;
}

static struct strgrp_bin *
add_bin(struct strgrp * const grp, const char * const str,
        void * const data) {
    struct strgrp_bin * b = new_bin(grp, str, data);
    if (!b) {
        return NULL;
    }
    list_add(&grp->bins, &b->list);
    grp->n_bins++;
    return b;
}

static size_t
rehash(const void *e, void *unused) {
    return hash_string(((struct strgrp_map *)e)->key);
}

static bool
hteq(const void * const e, void * const str) {
    return strcmp(((struct strgrp_map *)e)->key, str) == 0;
}

static struct strgrp_map *
lookup(struct strgrp * const ctx, const char * const str) {
    return (struct strgrp_map *)htable_get(&ctx->known, hash_string(str), &hteq, str);
}

struct strgrp *
strgrp_new(const double threshold) {
    struct strgrp * ctx = talloc_zero(NULL, struct strgrp);
    ctx->threshold = threshold;
    htable_init(&ctx->known, rehash, NULL);
    list_head_init(&ctx->bins);
    return ctx;
}

static bool
cache(struct strgrp * const grp, struct strgrp_bin * const bin,
        const char * const str, void * const data) {
    if (lookup(grp, str)) {
        return true;
    }
    struct strgrp_map * d = talloc_zero(grp, struct strgrp_map);
    d->key = talloc_strdup(grp, str);
    d->bin = bin;
    return htable_add(&grp->known, hash_string(str), d);
}

struct bin_score {
    struct strgrp_bin * bin;
    double score;
};

struct strgrp_bin *
strgrp_bin_for(struct strgrp * const ctx, const char * const str) {
    if (!ctx->n_bins) {
        return NULL;
    }
    const struct strgrp_map * const m = lookup(ctx, str);
    if (m) {
        return m->bin;
    }
    struct strgrp_bin ** bins = malloc(sizeof(struct strgrp_bin *) * ctx->n_bins);
    assert(bins);
    struct bin_score * scores = malloc(sizeof(struct bin_score) * ctx->n_bins);
    assert(scores);
    {
        int i = 0;
        struct strgrp_bin * bin;
        list_for_each(&ctx->bins, bin, list) {
            bins[i++] = bin;
        }
    }
    int i;
    #pragma omp parallel for schedule(dynamic)
    for (i = 0; i < ctx->n_bins; i++) {
        if (should_bin_score(ctx, bins[i], str)) {
            scores[i].bin = bins[i];
            scores[i].score = bin_score(bins[i], str);
        }
    }
    struct bin_score * max = NULL;
    for (i = 0; i < ctx->n_bins; i++) {
        if (!max || scores[i].score > max->score) {
            max = &scores[i];
        }
    }
    free(bins);
    free(scores);
    return (max && max->score > ctx->threshold) ? max->bin : NULL;
}

struct strgrp_bin *
strgrp_add(struct strgrp * const ctx, const char * const str,
        void * const data) {
    bool inserted = false;
    struct strgrp_bin * pick = strgrp_bin_for(ctx, str);
    if (pick) {
        inserted = add_item(pick, str, data);
    } else {
        pick = add_bin(ctx, str, data);
        inserted = (NULL != pick);
    }
    if (inserted) {
        assert(NULL != pick);
        cache(ctx, pick, str, data);
    }
    return pick;
}

struct strgrp_iter *
strgrp_iter_new(struct strgrp * const ctx) {
    struct strgrp_iter * iter = talloc_zero(ctx, struct strgrp_iter);
    if (!iter) {
        return NULL;
    }
    iter->head = &ctx->bins;
    return iter;
}

struct strgrp_bin *
strgrp_iter_next(struct strgrp_iter * const iter) {
    if (!iter->current) {
        iter->current = list_top(iter->head, struct strgrp_bin, list);
    } else {
        iter->current = list_next(iter->head, iter->current, list);
    }
    return iter->current;
}

void
strgrp_iter_free(struct strgrp_iter * const iter) {
    talloc_free(iter);
}

struct strgrp_bin_iter *
strgrp_bin_iter_new(struct strgrp_bin * const bin) {
    struct strgrp_bin_iter * iter = talloc_zero(bin, struct strgrp_bin_iter);
    if (!iter) {
        return NULL;
    }
    iter->head = &bin->items;
    return iter;
}

struct strgrp_item *
strgrp_bin_iter_next(struct strgrp_bin_iter * const iter) {
    if (!iter->current) {
        iter->current = list_top(iter->head, struct strgrp_item, list);
    } else {
        iter->current = list_next(iter->head, iter->current, list);
    }
    return iter->current;
}

void
strgrp_bin_iter_free(struct strgrp_bin_iter * iter) {
    talloc_free(iter);
}

char *
strgrp_bin_key(struct strgrp_bin * const bin) {
    return bin->key;
}

char *
strgrp_item_key(const struct strgrp_item * const item) {
    return item->key;
}

void *
strgrp_item_value(const struct strgrp_item * const item) {
    return item->value;
}

void
strgrp_free(struct strgrp * const ctx) {
    talloc_free(ctx);
}

void
strgrp_free_cb(struct strgrp * const ctx, void (*cb)(void * data)) {
    struct strgrp_bin * bin;
    struct strgrp_item * item;
    list_for_each(&ctx->bins, bin, list) {
        list_for_each(&bin->items, item, list) {
            cb(item->value);
        }
    }
    strgrp_free(ctx);
}

#include <stdio.h>

static void
print_item(const struct strgrp_item * item) {
    printf("\t%s\n", item->key);
}

static void
print_bin(const struct strgrp_bin * const bin) {
    struct strgrp_item * item;
    printf("%s:\n", bin->key);
    list_for_each(&bin->items, item, list) {
        print_item(item);
    }
    printf("\n");
}

void
strgrp_print(const struct strgrp * const ctx) {
    struct strgrp_bin * bin;
    list_for_each(&ctx->bins, bin, list) {
        print_bin(bin);
    }
}

#ifdef DEFINE_MAIN
#include <stdlib.h>

int
main(int argc, char ** argv) {
    FILE * const f = fdopen(0, "r");
#define BUF_SIZE 512
    char * buf = malloc(BUF_SIZE);
    struct strgrp * grp = strgrp_new(0.85);
    while(fgets(buf, BUF_SIZE, f)) {
        buf[strcspn(buf, "\r\n")] = '\0';
        if (!strgrp_add(grp, buf, NULL)) {
            printf("Failed to classify %s\n", buf);
            break;
        }
    }
    strgrp_print(grp);
    strgrp_free(grp);
    free(buf);
    fclose(f);
    return 0;
}
#endif /* DEFINE_MAIN */
