/*
 * KLEE header stub for compilation outside the KLEE environment.
 * The actual klee_make_symbolic is provided by the KLEE runtime.
 * This header allows the harness to compile to LLVM bitcode.
 */

#ifndef KLEE_KLEE_H
#define KLEE_KLEE_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Core KLEE intrinsics */
void klee_make_symbolic(void *addr, size_t nbytes, const char *name);
void klee_assume(int condition);
void klee_assert(int condition);

/* Silent versions (no output on failure) */
void klee_silent_exit(int status);

/* Prefer one path over another */
void klee_prefer_cex(void *object, int condition);

/* Mark memory as possibly uninitialized */
void klee_check_memory_access(const void *address, size_t size);

/* For testing */
int klee_range(int begin, int end, const char *name);
int klee_int(const char *name);

#ifdef __cplusplus
}
#endif

#endif /* KLEE_KLEE_H */
