#include <klee/klee.h>

int main(void) {
    int *p;
    klee_make_symbolic(&p, sizeof(p), "p");

    return *p;
}