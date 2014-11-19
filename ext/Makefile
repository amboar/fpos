#CFLAGS=-I. -O2
CFLAGS=-I. -ggdb -O2 -pg
#CFLAGS=-I. -ggdb -pg -O2 -fprofile-arcs -ftest-coverage
LDFLAGS=
LDFLAGS=-pg
#LDFLAGS=-pg -fprofile-arcs -ftest-coverage

OBJS = strgrp.o \
       lcs.o \
       ccan/hash/hash.o \
       ccan/htable/htable.o \
       ccan/list/list.o \
       ccan/str/debug.o \
       ccan/str/str.o \
       ccan/talloc/talloc.o

BINS = strgrp

strgrp: ${OBJS}

clean:
	rm -f ${OBJS} ${BINS} *.gcno *.gcda *.gcov gmon.out

.PHONY: clean
