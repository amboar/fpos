CFLAGS = -I. -O2
CFLAGS += -ggdb
LDFLAGS =
LDLIBS = -lm

CFLAGS += -fopenmp
LDFLAGS += -fopenmp

SRCS = \
       ccan/block_pool/block_pool.c \
       ccan/hash/hash.c \
       ccan/heap/heap.c \
       ccan/htable/htable.c \
       ccan/likely/likely.c \
       ccan/list/list.c \
       ccan/str/debug.c \
       ccan/strgrp/genann.c \
       ccan/strgrp/strgrp.c \
       ccan/stringmap/stringmap.c \
       ccan/str/str.c \
       ccan/take/take.c
       ccan/talloc/talloc.c \
       ccan/tal/str/str.c \
       ccan/tal/tal.c \
       ccan/tal/talloc/talloc.c \

OBJS = $(SRCS:%.c=%.o)

test: test.o $(OBJS)

.PHONY: clean
clean:
	rm -f $(OBJS) test.o
