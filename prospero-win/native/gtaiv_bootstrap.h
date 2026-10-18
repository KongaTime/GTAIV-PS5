/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GTAIV_BOOTSTRAP_H
#define GTAIV_BOOTSTRAP_H
/* 0: ready without touching graphics; 1: ready, restart before GPU use;
 * negative: failed. The prefix marker suppresses the screen after restart. */
int gtaiv_bootstrap(const char *data_root,const char *app_root);
#endif
