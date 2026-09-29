/* A dependency-free JNI implementation; arguments are intentionally unused. */
#ifndef MARKER
#error MARKER must be supplied by the pinned build
#endif
__attribute__((visibility("default")))
int Java_lab_mho900_loader_ProbeActivity_marker(void *environment, void *class_object) {
    (void)environment;
    (void)class_object;
    return MARKER;
}
