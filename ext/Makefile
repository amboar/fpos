#CFLAGS=-I. -O2
#CFLAGS=-I. -ggdb -pg -fwrapv -Wall -Wstrict-prototypes -fopenmp
#CFLAGS=-I. -ggdb -pg -O2 -fprofile-arcs -ftest-coverage
CFLAGS=-I. -O2 -fwrapv -Wall -Wstrict-prototypes -fopenmp
#LDFLAGS=-fopenmp -fsanitize=address
#LDFLAGS=-pg -fprofile-arcs -ftest-coverage -fopenmp
LDFLAGS=-fopenmp

CCAN = ccan/block_pool/block_pool.o \
       ccan/str/debug.o \
       ccan/str/str.o \
       ccan/stringmap/stringmap.o \
       ccan/talloc/talloc.o
TEST_CCAN = ccan/tap/tap.o

TEST_SRCS = $(wildcard test/api_*.c)

OBJS = strgrp.o ${CCAN}
TEST_OBJS = $(TEST_SRCS:%.c=%.o) ${TEST_CCAN} ${OBJS}

BINS = strgrp
TEST_BINS = $(TEST_SRCS:%.c=%)


all: strgrp

check: $(TEST_BINS)
	$(patsubst %,./%;,$^)

$(TEST_BINS):%:%.o ${OBJS} ${TEST_CCAN}

strgrp: ${OBJS}

clean:
	rm -f ${TEST_BINS} ${TEST_OBJS} ${OBJS} ${BINS} *.gcno *.gcda *.gcov gmon.out

.PHONY: clean
