#CFLAGS=-I. -O2
#CFLAGS=-I. -ggdb -O2 -pg -fwrapv -Wall -Wstrict-prototypes -DDEFINE_MAIN -fopenmp -fsanitize=address
CFLAGS=-I. -ggdb -O2 -pg -fwrapv -Wall -Wstrict-prototypes -DDEFINE_MAIN -fopenmp
#CFLAGS=-I. -ggdb -pg -O2 -fprofile-arcs -ftest-coverage
#LDFLAGS=-fopenmp -fsanitize=address
LDFLAGS=-fopenmp
#LDFLAGS=-pg -fprofile-arcs -ftest-coverage

OBJS = strgrp.o \
       ccan/block_pool/block_pool.o \
       ccan/str/debug.o \
       ccan/str/str.o \
       ccan/stringmap/stringmap.o \
       ccan/talloc/talloc.o

BINS = strgrp

strgrp: ${OBJS}

clean:
	rm -f ${OBJS} ${BINS} *.gcno *.gcda *.gcov gmon.out

.PHONY: clean
