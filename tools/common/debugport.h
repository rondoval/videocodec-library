/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * debugport.h - lines to Emu68's debug log (the PiStorm debug address), for
 * the test tools: VCTest's MARK, by which the suite proves the log it captures
 * is this machine's.
 */
#ifndef TOOLS_DEBUGPORT_H
#define TOOLS_DEBUGPORT_H

#include <stdarg.h>

void debugport_puts(const char *s);
void debugport_vprintf(const char *fmt, va_list ap);
void debugport_printf(const char *fmt, ...);

#endif /* TOOLS_DEBUGPORT_H */
