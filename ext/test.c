#include "config.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ccan/strgrp/strgrp.h"

int main(void) {
    FILE *f;
    char *buf;
    struct strgrp *ctx;
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
    strgrp_free(ctx);
    free(buf);
    fclose(f);
    return 0;
}
