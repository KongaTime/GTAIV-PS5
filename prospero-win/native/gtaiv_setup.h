/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GTAIV_SETUP_H
#define GTAIV_SETUP_H
#include <stddef.h>
typedef void (*GtaivProgress)(void *context, unsigned percent, const char *message);
/* Returns zero only after validation and any episode preparation completes. */
int gtaiv_prepare_game(const char *game, const char *state, GtaivProgress progress,
                       void *context, char *error, size_t error_size);
int gtaiv_copy_template(const char *source, const char *destination,
                        GtaivProgress progress, void *context,
                        char *error, size_t error_size);
#endif
