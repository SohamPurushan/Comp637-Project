#include <stdio.h>

int main() {
    int x = 5;
    int *p = &x;

    if (p != NULL) {
        *p = 7;
    }

    return 0;
}