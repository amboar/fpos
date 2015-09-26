#include "config.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ccan/strgrp/strgrp.h"

int main(void) {
    FILE *f;
    char *buf;
    struct strgrp *ctx;
    struct strgrp_iter *iter;
    const struct strgrp_grp *grp;
    struct strgrp_grp_iter *grp_iter;
    const struct strgrp_item *item;

    f = fdopen(0, "r");
#define BUF_SIZE 512
    buf = malloc(BUF_SIZE);
    ctx = strgrp_new(0.85);
    while(fgets(buf, BUF_SIZE, f)) {
        buf[strcspn(buf, "\r\n")] = '\0';
        if (!strgrp_add(ctx, buf, NULL)) {
            printf("Failed to classify %s\n", buf);
        }
    }
    strgrp_print(ctx);

    strgrp_iter_free(iter);
    strgrp_free(ctx);
    free(buf);
    fclose(f);
    return 0;
}
