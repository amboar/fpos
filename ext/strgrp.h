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
#ifndef STRGRP_H
#define STRGRP_H
#include <stdbool.h>

struct strgrp;
struct strgrp_iter;
struct strgrp_grp;
struct strgrp_grp_iter;
struct strgrp_item;

struct strgrp *
strgrp_new(double threshold);

struct strgrp_grp *
strgrp_grp_for(struct strgrp *ctx, const char *str);

struct strgrp_grp *
strgrp_add(struct strgrp *ctx, const char *str, void *data);

struct strgrp_iter *
strgrp_iter_new(struct strgrp *ctx);

struct strgrp_grp *
strgrp_iter_next(struct strgrp_iter *iter);

char *
strgrp_grp_key(struct strgrp_grp *grp);

void
strgrp_iter_free(struct strgrp_iter *iter);

struct strgrp_grp_iter *
strgrp_grp_iter_new(struct strgrp_grp *grp);

struct strgrp_item *
strgrp_grp_iter_next(struct strgrp_grp_iter *iter);

void
strgrp_grp_iter_free(struct strgrp_grp_iter *iter);

char *
strgrp_item_key(const struct strgrp_item *item);

void *
strgrp_item_value(const struct strgrp_item *item);

void
strgrp_free(struct strgrp *ctx);

void
strgrp_free_cb(struct strgrp *ctx, void (*cb)(void *data));

void
strgrp_print(const struct strgrp *ctx);
#endif
