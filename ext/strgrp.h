/*
 *  Group similar strings
 *  Copyright (C) 2014-2015  Andrew Jeffery <andrew@aj.id.au>
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/
#ifndef STRGRP_H
#define STRGRP_H
#include <stdbool.h>

/**
 * The primary string clustering object
 */
struct strgrp;

/**
 * Iterates the generated groups
 */
struct strgrp_iter;

/**
 * Represents a group.
 */
struct strgrp_grp;

/**
 * Iterates items in a group
 */
struct strgrp_grp_iter;

/**
 * Represents an item in a group
 */
struct strgrp_item;

/**
 * Constructs a new strgrp instance.
 * @threshold: A value in [0.0, 1.0] describing the desired similarity of
 *     strings in a cluster
 *
 * @return A heap-allocated strgrp instance, or NULL if initialisation fails.
 * Ownership of the pointer resides with the caller, which must be freed with
 * strgrp_free.
 */
struct strgrp *
strgrp_new(double threshold);

/**
 * Find a group which best matches the provided string key.
 * @ctx: The strgrp instance to search
 * @str: The string key to cluster
 *
 * The returned group is the group providing the maximum score that is above
 * the configured threshold.
 *
 * @return A matched group, or NULL if no reasonable group is found. Ownership
 * of the returned pointer resides with the strgrp instance and it becomes
 * invalid if the strgrp instance is freed.
 */
const struct strgrp_grp *
strgrp_grp_for(struct strgrp *ctx, const char *str);

/**
 * Add a string key and arbitrary data value (together, an item) to the
 * appropriate group.
 *
 * @ctx: The strgrp instance to add the string and data
 * @str: The string key used to select a group. The caller retains ownership of
 *     the pointer and may free or change the memory prior to freeing the
 *     strgrp instance.
 * @data: The data to attach to the group's new entry. The caller retains
 *     ownership of the pointer, but for correctness its lifetime should be at
 *     least equal to the lifetime of the strgrp instance.
 *
 * @return The group to which the item was added. Ownership of the returned
 * pointer resides with the strgrp instance and it becomes invalid if the
 * strgrp instance is freed.
 */
const struct strgrp_grp *
strgrp_add(struct strgrp *ctx, const char *str, void *data);

/**
 * Create an iterator over the current groups.
 * @ctx: The strgrp instance to iterate over
 *
 * @return An iterator structure, or NULL if a failure occurred. Ownership of
 * the returned pointer is with the caller, but its useful lifetime is bounded
 * by the lifetime of the strgrp instance. The caller must pass the pointer
 * strgrp_iter_free. It is invalid to call strgrp_iter_next on the returned
 * pointer after the strgrp instance has been freed.
 */
struct strgrp_iter *
strgrp_iter_new(struct strgrp *ctx);

/**
 * Extract the next group from a group iterator
 * @iter: The iterator in question
 *
 * Example:
 *
 *     #include <assert.h>
 *     #include <string.h>
 *     #include <stdio.h>
 *     #include "strgrp.h"
 *
 *     int main(int argc, char *argv[]) {
 *         struct strgrp *ctx = strgrp_new(0.85);
 *         assert(ctx);
 *         {
 *             struct strgrp_grp *grp = strgrp_add(ctx, "foo", NULL);
 *             assert(grp);
 *         }
 *         struct strgrp_iter *iter = strgrp_iter_new(ctx);
 *         assert(iter);
 *         struct strgrp_grp *grp;
 *         while(NULL != (grp = strgrp_iter_next(iter))) {
 *             printf("%s\n", strgrp_grp_key(grp));
 *         }
 *         strgrp_iter_free(iter);
 *         strgrp_free(ctx);
 *         return 0;
 *     }
 *
 * @return The next group in the iterator or NULL if no further groups exist.
 * Ownership of the returned pointer resides with the strgrp instance and
 * becomes invalid if the strgrp instance is freed.
 */
const struct strgrp_grp *
strgrp_iter_next(struct strgrp_iter *iter);

/**
 * Clean up a group iterator instance
 * @iter: The iterator to free
 */
void
strgrp_iter_free(struct strgrp_iter *iter);

/**
 * Extract the key for a group.
 * @grp: A strgrp_grp instance obtained from a strgrp_iter
 *
 * A group's key is the input string that caused the creation of the group.
 *
 * @return The group key. Ownership of the pointer resides with the grp
 * parameter and by extension the strgrp instance. The caller must duplicate
 * the string if the content is required beyond the lifetime of the strgrp
 * instance.
 */
const char *
strgrp_grp_key(const struct strgrp_grp *grp);

/**
 * Create an iterator over items in the provided group
 * @grp: The group whose items to iterate over
 *
 * @return An iterator structure, or NULL if a failure occurred. Ownership of
 * the returned pointer is with the caller, but its useful lifetime is bounded
 * by the lifetime of the strgrp instance. The caller must pass the pointer
 * strgrp_grp_iter_free. It is invalid to call strgrp_grp_iter_next on the
 * returned pointer after the strgrp instance has been freed.
 */
struct strgrp_grp_iter *
strgrp_grp_iter_new(const struct strgrp_grp *grp);

/**
 * Extract the next item from a item iterator
 * @iter: The iterator in question
 *
 * For example use see the documentation on strgrp_item_key.
 *
 * @return The next group in the iterator or NULL if no further items exist.
 * Ownership of the returned pointer resides with the strgrp instance and
 * becomes invalid if the strgrp instance is freed.
 */
const struct strgrp_item *
strgrp_grp_iter_next(struct strgrp_grp_iter *iter);

/**
 * Clean up an item iterator instance
 * @iter: The iterator to free
 */
void
strgrp_grp_iter_free(struct strgrp_grp_iter *iter);

/**
 * Extract the key for an item
 * @item: The item in question
 *
 * The key is the string input string which generated the item in the cluster.
 *
 * Example:
 *
 *     #include <assert.h>
 *     #include <string.h>
 *     #include <stdio.h>
 *     #include "strgrp.h"
 *
 *     int main(int argc, char *argv[]) {
 *         struct strgrp *ctx = strgrp_new(0.85);
 *         assert(ctx);
 *         {
 *             struct strgrp_grp *grp = strgrp_add(ctx, "foo", NULL);
 *             assert(grp);
 *         }
 *         struct strgrp_iter *iter = strgrp_iter_new(ctx);
 *         assert(iter);
 *         struct strgrp_grp *grp;
 *         while(NULL != (grp = strgrp_iter_next(iter))) {
 *             printf("%s\n", strgrp_grp_key(grp));
 *             struct strgrp_grp_iter *grp_iter = strgrp_grp_iter_new(grp);
 *             struct strgrp_item *item;
 *             while(NULL != (item = strgrp_grp_iter_next(grp_iter))) {
 *                  printf("\t%s\n", strgrp_item_key(item));
 *             }
 *             strgrp_grp_iter_free(grp_iter);
 *         }
 *         strgrp_iter_free(iter);
 *         strgrp_free(ctx);
 *         return 0;
 *     }
 *
 * @return The item key. Ownership of the pointer resides with the item
 * parameter and by extension the strgrp instance. The caller must duplicate
 * the string if the content is required beyond the lifetime of the strgrp
 * instance.
 */
const char *
strgrp_item_key(const struct strgrp_item *item);

/**
 * Extract the value for an item
 * @item: The item in question
 *
 * The value is the arbitrary pointer associated with the input string
 *
 * @return The item value. The ownership of the pointer does not reside with
 * the strgrp instance, but for correctness should exceed the lifetime of the
 * strgrp instance.
 */
void *
strgrp_item_value(const struct strgrp_item *item);

/**
 * Destroy the strgrp instance
 * @ctx: The strgrp instance in question
 */
void
strgrp_free(struct strgrp *ctx);

/**
 * Destroy the strgrp instance, but not before applying cb() to each item's value element
 * @ctx: The strgrp instance in question
 * @cb: The callback to execute against each item's value. This might be used
 *      to free the value data.
 */
void
strgrp_free_cb(struct strgrp *ctx, void (*cb)(void *data));


/**
 * Dump the groupings to stdout.
 * @ctx: The strgrp instance in question
 */
void
strgrp_print(const struct strgrp *ctx);
#endif
