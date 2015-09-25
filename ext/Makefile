CFLAGS = -I. -O2
CFLAGS += -ggdb
LDFLAGS =
LDLIBS = -lm

CFLAGS += -fopenmp
LDFLAGS += -fopenmp

SRCS = ccan/talloc/talloc.c \
       ccan/strgrp/strgrp.c \
       ccan/block_pool/block_pool.c \
       ccan/likely/likely.c \
       ccan/str/str.c \
       ccan/str/debug.c \
       ccan/tal/talloc/talloc.c \
       ccan/tal/tal.c \
       ccan/tal/str/str.c \
       ccan/list/list.c \
       ccan/htable/htable.c \
       ccan/stringmap/stringmap.c \
       ccan/hash/hash.c \
       ccan/take/take.c
OBJS = $(SRCS:%.c=%.o)

test: test.o $(OBJS)

.PHONY: clean
clean:
	rm -f $(OBJS) test.o
