int target(int *p) {
    return *p;   // feasible null dereference when p == NULL
}
