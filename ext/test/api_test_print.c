#include "test/helpers.h"

int main(void) {
    struct strgrp *ctx;

    plan_tests(1);
    create(ctx, DEFAULT_SIMILARITY);
    strgrp_add(ctx, "a", "1");
    strgrp_add(ctx, "a", "2");
    strgrp_add(ctx, "b", "3");
    strgrp_print(ctx);
    strgrp_free(ctx);
    pass("No errors");
    return exit_status();
}
