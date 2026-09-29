#include "fram-read.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
struct control { unsigned calls, fail_at; int result; unsigned generation; };
static int simulated(void *opaque, struct fram_rdwr *r) {
    struct control *c = opaque;
    assert(r->nmsgs == 2);
    struct fram_msg *a = r->msgs, *b = r->msgs + 1;
    assert(a->addr == 0x50 && a->flags == 0 && a->len == 2);
    assert(b->addr == 0x50 && b->flags == 1 && b->len == 16);
    unsigned offset = ((unsigned)a->buf[0] << 8) | a->buf[1];
    assert(offset == c->calls * 16 && offset <= 8176);
    ++c->calls;
    for (unsigned i = 0; i < 16; ++i) b->buf[i] = (uint8_t)((offset+i)/31+c->generation);
    return c->calls == c->fail_at ? c->result : 2;
}
int main(void) {
    uint8_t image[8192], other[8192]; size_t completed;
    struct control c = {0};
    assert(fram_image(simulated, &c, image, &completed) == 0);
    assert(completed == 8192 && c.calls == 512);
    for (unsigned i = 0; i < 8192; ++i) assert(image[i] == (uint8_t)(i/31));
    const int failures[] = {-1, 0, 1, 3};
    for (unsigned j = 0; j < 4; ++j) {
        memset(other, 0xa5, sizeof(other));
        c = (struct control){.fail_at=4, .result=failures[j]};
        assert(fram_image(simulated, &c, other, &completed) == -2);
        assert(completed == 48 && c.calls == 4);
        assert(memcmp(image, other, 48) == 0);
        for (unsigned i = 48; i < 8192; ++i) assert(other[i] == 0xa5);
    }
    const uint32_t invalid[] = {1, 8177, 8192, UINT32_MAX};
    c = (struct control){0};
    for (unsigned j = 0; j < 4; ++j)
        assert(fram_page(simulated, &c, invalid[j], other) == -1);
    assert(c.calls == 0);
    assert(fram_page(NULL, &c, 0, other) == -1);
    assert(fram_page(simulated, &c, 0, NULL) == -1);
    assert(fram_image(simulated, &c, other, NULL) == -1);
    c = (struct control){0};
    assert(fram_image(simulated, &c, other, &completed) == 0);
    assert(memcmp(image, other, 8192) == 0);
    c = (struct control){.generation=1};
    assert(fram_image(simulated, &c, other, &completed) == 0);
    assert(memcmp(image, other, 8192) != 0);
    puts("pass = true\nfull_image_bytes = 8192\nfull_image_transactions = 512\nrejected_completion_results = [-1, 0, 1, 3]\nbounds_controls = 4\nrepeat_equality_and_divergence = true");
}
