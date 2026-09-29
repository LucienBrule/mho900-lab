#ifndef MHO900_FRAM_READ_H
#define MHO900_FRAM_READ_H
#include <stddef.h>
#include <stdint.h>
/* Offline descriptions only: no device or syscall implementation. */
struct fram_msg { uint16_t addr, flags, len; uint8_t *buf; };
struct fram_rdwr { struct fram_msg *msgs; uint32_t nmsgs; };
_Static_assert(sizeof(void *) == 8, "64-bit ABI");
_Static_assert(sizeof(struct fram_msg) == 16, "ARM64 message size");
_Static_assert(offsetof(struct fram_msg, buf) == 8, "ARM64 buffer offset");
_Static_assert(sizeof(struct fram_rdwr) == 16, "ARM64 request size");
_Static_assert(offsetof(struct fram_rdwr, nmsgs) == 8, "ARM64 count offset");
typedef int (*fram_transfer)(void *, struct fram_rdwr *);
/* Commit output only after exactly two messages; never retry automatically. */
static inline int fram_page(fram_transfer transfer, void *context,
                            uint32_t offset, uint8_t out[16]) {
    if (!transfer || !out || offset > 8176u || offset % 16u) return -1;
    uint8_t selector[2] = {(uint8_t)(offset >> 8), (uint8_t)offset};
    uint8_t scratch[16] = {0};
    struct fram_msg messages[2] = {{0x50, 0, 2, selector}, {0x50, 1, 16, scratch}};
    struct fram_rdwr request = {messages, 2};
    if (transfer(context, &request) != 2) return -2;
    for (size_t i = 0; i < 16; ++i) out[i] = scratch[i];
    return 0;
}
/* Only the completed prefix is valid after failure. Preserve failures upstream. */
static inline int fram_image(fram_transfer transfer, void *context,
                             uint8_t out[8192], size_t *completed) {
    if (!completed) return -1;
    *completed = 0;
    if (!out || !transfer) return -1;
    for (uint32_t offset = 0; offset < 8192; offset += 16) {
        int result = fram_page(transfer, context, offset, out + offset);
        if (result) return result;
        *completed += 16;
    }
    return 0;
}
#endif
