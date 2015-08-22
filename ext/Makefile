#CFLAGS=-I. -O2
#CFLAGS=-I. -ggdb -O2 -pg -fwrapv -Wall -Wstrict-prototypes -fopenmp -fsanitize=address
#CFLAGS=-I. -ggdb -pg -O2 -fprofile-arcs -ftest-coverage
CFLAGS=-I. -O2 -fwrapv -Wall -Wstrict-prototypes -fopenmp
#LDFLAGS=-fopenmp -fsanitize=address
#LDFLAGS=-pg -fprofile-arcs -ftest-coverage
LDFLAGS=-fopenmp

CCAN = ccan/block_pool/block_pool.o \
       ccan/str/debug.o \
       ccan/str/str.o \
       ccan/stringmap/stringmap.o \
       ccan/talloc/talloc.o
OBJS = strgrp.o ${CCAN}
BINS = strgrp

all: strgrp

strgrp: ${OBJS}

strgrp.o: CFLAGS += -DDEFINE_MAIN

clean:
	rm -f ${OBJS} ${BINS} *.gcno *.gcda *.gcov gmon.out

.PHONY: clean
