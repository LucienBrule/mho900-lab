/* Bounded passive private-cache reader, derived from the pinned APK cached reader. No attachment, target calls or
 * fallback. Linux AArch64 UAPI layout provenance is recorded in inputs.toml. */
typedef unsigned long U;
typedef long S;
typedef unsigned int W;
typedef unsigned char B;
#define PIN "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e"
#define RAW_BAND 0xbbcce4UL
#define EFFECTIVE_BAND 0xbbcce8UL
#define LIB_SIZE 12453760UL
#define APK_SIZE 38166679UL
#define APK_OFFSET 0xf05000UL
#define APK_PIN "6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b"
#define MAP_CAP 1048576UL
static U length(const char *s) {
  U n = 0;
  while (s[n])
    n++;
  return n;
}
static int equal(const void *a, const void *b, U n) {
  const B *x = a, *y = b;
  for (U i = 0; i < n; i++)
    if (x[i] != y[i])
      return 0;
  return 1;
}
static void copy(void *a, const void *b, U n) {
  B *x = a;
  const B *y = b;
  for (U i = 0; i < n; i++)
    x[i] = y[i];
}
static int same(const char *a, const char *b) {
  return length(a) == length(b) && equal(a, b, length(a));
}
static int digit(char c, int base) {
  if (c >= '0' && c <= '9')
    return c - '0';
  if (base == 16 && c >= 'a' && c <= 'f')
    return c - 'a' + 10;
  return -1;
}
static int number(const char **p, int base, U *v) {
  U n = 0, k = 0;
  int d;
  while ((d = digit(**p, base)) >= 0 && d < base) {
    if (n > (~0UL - (U)d) / (U)base)
      return 0;
    n = n * (U)base + (U)d;
    (*p)++;
    k++;
  }
  *v = n;
  return k != 0;
}
static void spaces(const char **p) {
  while (**p == ' ' || **p == '\t')
    (*p)++;
}
static U le(const B *p, U n) {
  U x = 0;
  for (U i = 0; i < n; i++)
    x |= (U)p[i] << (8 * i);
  return x;
}
static W rotate(W x, W n) { return (x >> n) | (x << (32 - n)); }
struct sha {
  W h[8];
  B buf[64];
  U bytes, used;
};
static const W constants[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
static void sha_block(struct sha *s, const B *p) {
  W w[64];
  for (U i = 0; i < 16; i++)
    w[i] = ((W)p[i * 4] << 24) | ((W)p[i * 4 + 1] << 16) |
           ((W)p[i * 4 + 2] << 8) | p[i * 4 + 3];
  for (U i = 16; i < 64; i++) {
    W a = w[i - 15], b = w[i - 2];
    w[i] = w[i - 16] + (rotate(a, 7) ^ rotate(a, 18) ^ (a >> 3)) + w[i - 7] +
           (rotate(b, 17) ^ rotate(b, 19) ^ (b >> 10));
  }
  W a = s->h[0], b = s->h[1], c = s->h[2], d = s->h[3], e = s->h[4],
    f = s->h[5], g = s->h[6], h = s->h[7];
  for (U i = 0; i < 64; i++) {
    W t = h + (rotate(e, 6) ^ rotate(e, 11) ^ rotate(e, 25)) +
          ((e & f) ^ (~e & g)) + constants[i] + w[i];
    W u = (rotate(a, 2) ^ rotate(a, 13) ^ rotate(a, 22)) +
          ((a & b) ^ (a & c) ^ (b & c));
    h = g;
    g = f;
    f = e;
    e = d + t;
    d = c;
    c = b;
    b = a;
    a = t + u;
  }
  s->h[0] += a;
  s->h[1] += b;
  s->h[2] += c;
  s->h[3] += d;
  s->h[4] += e;
  s->h[5] += f;
  s->h[6] += g;
  s->h[7] += h;
}
static void sha_init(struct sha *s) {
  static const W initial[] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                              0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
  copy(s->h, initial, 32);
  s->bytes = 0;
  s->used = 0;
}
static void sha_add(struct sha *s, const B *p, U n) {
  s->bytes += n;
  while (n--) {
    s->buf[s->used++] = *p++;
    if (s->used == 64) {
      sha_block(s, s->buf);
      s->used = 0;
    }
  }
}
static void sha_end(struct sha *s, char out[65]) {
  U bits = s->bytes * 8;
  B b = 0x80;
  sha_add(s, &b, 1);
  b = 0;
  while (s->used != 56)
    sha_add(s, &b, 1);
  for (int i = 7; i >= 0; i--) {
    b = (B)(bits >> (i * 8));
    sha_add(s, &b, 1);
  }
  static const char hex[] = "0123456789abcdef";
  for (U i = 0; i < 32; i++) {
    B x = (B)(s->h[i / 4] >> (24 - 8 * (i % 4)));
    out[i * 2] = hex[x >> 4];
    out[i * 2 + 1] = hex[x & 15];
  }
  out[64] = 0;
}
static void hash_bytes(const void *p, U n, char out[65]) {
  struct sha s;
  sha_init(&s);
  sha_add(&s, p, n);
  sha_end(&s, out);
}
static int validate_elf(const B *p, U n) {
  if (n < 512 || !equal(p, "\177ELF\2\1\1", 7) || le(p + 16, 2) != 3 ||
      le(p + 18, 2) != 183 || le(p + 20, 4) != 1 || le(p + 52, 2) != 64 ||
      le(p + 32, 8) != 64 || le(p + 54, 2) != 56 || le(p + 56, 2) != 8)
    return 0;
  U loads = 0;
  for (U i = 0; i < 8; i++) {
    const B *q = p + 64 + i * 56;
    if (le(q, 4) != 1)
      continue;
    if (loads == 0) {
      if (le(q + 4, 4) != 5 || le(q + 8, 8) || le(q + 16, 8) ||
          le(q + 32, 8) != 0xb689d4 || le(q + 40, 8) != 0xb689d4 ||
          le(q + 48, 8) != 4096)
        return 0;
    } else if (loads == 1) {
      if (le(q + 4, 4) != 6 || le(q + 8, 8) != 0xb68c00 ||
          le(q + 16, 8) != 0xb69c00 || le(q + 32, 8) != 0x77200 ||
          le(q + 40, 8) != 0x314ad10 || le(q + 48, 8) != 4096)
        return 0;
    } else
      return 0;
    loads++;
  }
  return loads == 2;
}
static int parse_starttime(const char *s, U pid, U *out) {
  const char *p = s;
  U actual;
  if (!number(&p, 10, &actual) || actual != pid || *p != ' ')
    return 0;
  const char *last = 0;
  for (; *p; p++)
    if (*p == ')')
      last = p;
  if (!last || last[1] != ' ')
    return 0;
  p = last + 2;
  for (U f = 3; f < 22; f++) {
    if (!*p || *p == '\n')
      return 0;
    while (*p && *p != ' ' && *p != '\n')
      p++;
    spaces(&p);
  }
  return number(&p, 10, out) && (*p == ' ' || *p == '\n');
}
struct row {
  U lo, hi, off, maj, min, ino;
  char perm[5];
  const char *path;
  U path_n;
};
static int row_parse(const char *p, struct row *r) {
  if (!number(&p, 16, &r->lo) || *p++ != '-' || !number(&p, 16, &r->hi) ||
      *p != ' ')
    return 0;
  spaces(&p);
  for (U i = 0; i < 4; i++) {
    if (!p[i] || p[i] == '\n')
      return 0;
    r->perm[i] = p[i];
  }
  r->perm[4] = 0;
  p += 4;
  spaces(&p);
  if (!number(&p, 16, &r->off))
    return 0;
  spaces(&p);
  if (!number(&p, 16, &r->maj) || *p++ != ':' || !number(&p, 16, &r->min))
    return 0;
  spaces(&p);
  if (!number(&p, 10, &r->ino))
    return 0;
  spaces(&p);
  r->path = p;
  r->path_n = 0;
  while (p[r->path_n] && p[r->path_n] != '\n')
    r->path_n++;
  return r->hi > r->lo && !(r->lo & 4095) && !(r->hi & 4095) &&
         !(r->off & 4095);
}
static int row_file(const struct row *r, const char *path, U dev, U ino) {
  U major = ((dev >> 8) & 0xfff) | ((dev >> 32) & 0xfffff000),
    minor = (dev & 255) | ((dev >> 12) & 0xffffff00);
  return r->maj == major && r->min == minor && r->ino == ino &&
         r->path_n == length(path) && equal(r->path, path, r->path_n);
}
/* APK-backed mode pins the complete container. Other entries share its inode. */
static int resolve_maps_ranges(const char *text, const char *path, U dev, U ino,
                               U *bias, U raw_band_va, U effective_band_va) {
  U found = 0, b = 0, previous = 0;
  const char *p = text;
  while (*p) {
    struct row r;
    if (!row_parse(p, &r) || r.lo < previous) return 0;
    previous = r.hi;
    if (row_file(&r, path, dev, ino) && r.off == APK_OFFSET && same(r.perm, "r-xp")) {
      if (found++) return 0;
      b = r.lo;
    }
    while (*p && *p != '\n') p++;
    if (*p) p++;
  }
  if (found != 1 || b > ~0UL - 0x3cb5000 || raw_band_va != RAW_BAND || effective_band_va != EFFECTIVE_BAND) return 0;
  U raw_band = 0, effective_band = 0, rx_pages = 0, data_pages = 0;
  p = text;
  while (*p) {
    struct row r;
    if (!row_parse(p, &r)) return 0;
    int identity = r.ino == ino &&
      r.maj == (((dev >> 8) & 0xfff) | ((dev >> 32) & 0xfffff000)) &&
      r.min == ((dev & 255) | ((dev >> 12) & 0xffffff00));
    int named = r.path_n == length(path) && equal(r.path, path, r.path_n);
    int deleted = r.path_n == length(path) + 10 && equal(r.path, path, length(path)) &&
      equal(r.path + length(path), " (deleted)", 10);
    if (identity || named || deleted) {
      if (!row_file(&r, path, dev, ino)) return 0;
      U size = r.hi - r.lo;
      if (r.off > ~0UL - size) return 0;
      U end = r.off + size;
      if (r.off < APK_OFFSET + ((LIB_SIZE + 4095) & ~4095UL) && end > APK_OFFSET) {
        if (r.off < APK_OFFSET || end > APK_OFFSET + ((LIB_SIZE + 4095) & ~4095UL)) return 0;
        U off = r.off - APK_OFFSET;
        int rx = off < 0xb69000 && size <= 0xb69000 - off &&
          r.lo == b + off && same(r.perm, "r-xp");
        int data = off >= 0xb68000 && off < 0xbe0000 && size <= 0xbe0000 - off &&
          r.lo == b + off + 4096 && (same(r.perm, "r--p") || same(r.perm, "rw-p"));
        if (!rx && !data) return 0;
        if (rx) rx_pages += size / 4096;
        if (data) data_pages += size / 4096;
        if (data && same(r.perm, "rw-p")) {
          if (b + raw_band_va >= r.lo && b + raw_band_va + 4 <= r.hi && off + b + raw_band_va - r.lo == 0xbbbce4) raw_band++;
          if (b + effective_band_va >= r.lo && b + effective_band_va + 4 <= r.hi && off + b + effective_band_va - r.lo == 0xbbbce8) effective_band++;
        }
      } else if (!(r.hi <= b || r.lo >= b + 0x3cb5000)) return 0;
    }
    while (*p && *p != '\n') p++;
    if (*p) p++;
  }
  if (rx_pages != 0xb69 || data_pages != 0x78 || raw_band != 1 || effective_band != 1) return 0;
  *bias = b;
  return 1;
}

static int resolve_maps(const char *text, const char *path, U dev, U ino,
                        U *bias) {
  return resolve_maps_ranges(text, path, dev, ino, bias, RAW_BAND, EFFECTIVE_BAND);
}
/* Compare only exact selected library rows; unrelated ART mappings may evolve.
 */
static const char *next_library_row(const char *p, const char *path, U dev,
                                    U ino, U *n) {
  while (*p) {
    const char *start = p;
    struct row r;
    if (!row_parse(p, &r))
      return 0;
    while (*p && *p != '\n')
      p++;
    if (*p)
      p++;
    if (row_file(&r, path, dev, ino)) {
      *n = (U)(p - start);
      return start;
    }
  }
  *n = 0;
  return p;
}
static int selected_maps_equal(const char *a, const char *b, const char *path,
                               U dev, U ino) {
  for (;;) {
    U an = 0, bn = 0;
    const char *ap = next_library_row(a, path, dev, ino, &an),
               *bp = next_library_row(b, path, dev, ino, &bn);
    if (!ap || !bp || an != bn)
      return 0;
    if (!an)
      return 1;
    if (!equal(ap, bp, an))
      return 0;
    a = ap + an;
    b = bp + bn;
  }
}

#ifndef READER_HOST_TEST
static S call(S n, U a, U b, U c, U d, U e, U f) {
  register U x0 __asm__("x0") = a, x1 __asm__("x1") = b, x2 __asm__("x2") = c,
                x3 __asm__("x3") = d, x4 __asm__("x4") = e,
                x5 __asm__("x5") = f;
  register S x8 __asm__("x8") = n;
  __asm__ volatile("svc 0"
                   : "+r"(x0)
                   : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5), "r"(x8)
                   : "memory");
  return (S)x0;
}
struct stat64 {
  U dev, ino;
  W mode, nlink, uid, gid;
  U rdev, pad1;
  S size;
  int blksize, pad2;
  S blocks, atime;
  U atime_ns;
  S mtime;
  U mtime_ns;
  S ctime;
  U ctime_ns;
  W unused[2];
};
_Static_assert(sizeof(struct stat64) == 128, "AArch64 stat size");
static char maps0[MAP_CAP], maps1[MAP_CAP], statbuf[8192], bootbuf[128],
    manifest[65536];
static U mn, pid, expected_start, observed_start, bias, bytes, calls, memopens,
    samples, requested_bytes;
static S err;
static const char *stage = "arguments", *mode = "positive", *libpath, *outpath,
                  *boot_expected;
static int accepted, repeat_ok, identity_ok, maps_ok, file_ok, evidence_error,
    full_maps_changed;
static S outfd = -1, libfd = -1, memfd = -1;
static char apkhash[65], libhash[65], hash1[65], hash2[65], boot_first[128], boot_last[128];
static struct stat64 sb, sa;
static U start_first, start_last;
#define MAX_TARGET_BYTES 16384UL
#define MAX_READS 160UL
#define WINDOW 0x700UL
#define REGISTRY 0xbe0f18UL
#define SETUP_VTABLE 0xb6c3a0UL
#define SETUP_TYPEINFO 0xb6c440UL
struct observation { U address, requested, round, anonymous; S result; char name[24]; };
static struct observation observations[MAX_READS];
static B owner[2][2048], work[2][WINDOW], reference[2][WINDOW];
static U owner_size[2], owner_count, owner_item, owner_base, owner_complete, work_pointer, reference_pointer;
static int pair_equal;

static S open_path(const char *p, U flags, U permissions) {
  return call(56, (U)-100, (U)p, flags, permissions, 0, 0);
}
static void close_fd(S fd) {
  if (fd >= 0 && call(57, (U)fd, 0, 0, 0, 0, 0) < 0)
    evidence_error = 1;
}
static void append(const char *s) {
  U n = length(s);
  if (n >= sizeof(manifest) - mn) {
    evidence_error = 1;
    return;
  }
  copy(manifest + mn, s, n);
  mn += n;
  manifest[mn] = 0;
}
static void uintout(U x, int base) {
  char b[32];
  U n = 0;
  do {
    b[n++] = "0123456789abcdef"[x % (U)base];
    x /= (U)base;
  } while (x);
  while (n) {
    char a[2] = {b[--n], 0};
    append(a);
  }
}
static void sintout(S x) {
  if (x < 0) {
    append("-");
    uintout((U)(-(x + 1)) + 1, 10);
  } else
    uintout((U)x, 10);
}
static void qstr(const char *s) {
  append("\"");
  for (U i = 0; s[i]; i++) {
    char a[2] = {s[i], 0};
    if (s[i] == '"' || s[i] == '\\')
      append("\\");
    if ((B)s[i] < 32) {
      append("?");
    } else
      append(a);
  }
  append("\"");
}
static void strfield(const char *k, const char *v) {
  append(k);
  append(" = ");
  qstr(v ? v : "");
  append("\n");
}
static void numfield(const char *k, U v) {
  append(k);
  append(" = ");
  uintout(v, 10);
  append("\n");
}
static void boolfield(const char *k, int v) {
  append(k);
  append(v ? " = true\n" : " = false\n");
}
static void hexfield(const char *k, U v) {
  append(k);
  append(" = \"0x");
  uintout(v, 16);
  append("\"\n");
}
static int save(const char *name, const void *data, U n) {
  S fd = call(56, (U)outfd, (U)name, 1 | 0x40 | 0x80 | 0x8000 | 0x80000, 0600,
              0, 0);
  if (fd < 0) {
    err = -fd;
    evidence_error = 1;
    return 0;
  }
  U done = 0;
  while (done < n) {
    S r = call(64, (U)fd, (U)((const B *)data + done), n - done, 0, 0, 0);
    if (r <= 0) {
      err = r < 0 ? -r : 5;
      evidence_error = 1;
      break;
    }
    done += (U)r;
  }
  if (call(82, (U)fd, 0, 0, 0, 0, 0) < 0)
    evidence_error = 1;
  close_fd(fd);
  return done == n && !evidence_error;
}
static S read_text(const char *p, char *b, U cap) {
  S fd = open_path(p, 0x80000, 0);
  if (fd < 0) {
    err = -fd;
    return -1;
  }
  U n = 0;
  while (n < cap - 1) {
    S r = call(63, (U)fd, (U)(b + n), cap - 1 - n, 0, 0, 0);
    if (r < 0) {
      err = -r;
      close_fd(fd);
      return -1;
    }
    if (!r) {
      b[n] = 0;
      close_fd(fd);
      return (S)n;
    }
    n += (U)r;
  }
  B extra;
  S r = call(63, (U)fd, (U)&extra, 1, 0, 0, 0);
  close_fd(fd);
  if (r != 0) {
    err = r < 0 ? -r : 75;
    return -1;
  }
  b[n] = 0;
  return (S)n;
}
static void procpath(char *out, const char *leaf) {
  U n = 0;
  const char *s = "/proc/";
  while (*s)
    out[n++] = *s++;
  char rev[24];
  U k = 0, x = pid;
  do {
    rev[k++] = (char)('0' + x % 10);
    x /= 10;
  } while (x);
  while (k)
    out[n++] = rev[--k];
  out[n++] = '/';
  while (*leaf)
    out[n++] = *leaf++;
  out[n] = 0;
}
static int metadata(const char *suffix, char *maps, U *mapsn, U *start,
                    char *boot) {
  char p[128], name[64];
  procpath(p, "stat");
  S n = read_text(p, statbuf, sizeof statbuf);
  if (n < 0)
    return 0;
  U i = 0;
  const char *a = "stat-";
  while (*a)
    name[i++] = *a++;
  a = suffix;
  while (*a)
    name[i++] = *a++;
  copy(name + i, ".txt", 5);
  if (!save(name, statbuf, (U)n) || !parse_starttime(statbuf, pid, start))
    return 0;
  observed_start = *start;
  if (*start != expected_start)
    return 0;
  n = read_text("/proc/sys/kernel/random/boot_id", bootbuf, sizeof bootbuf);
  if (n < 0)
    return 0;
  i = 0;
  a = "boot-";
  while (*a)
    name[i++] = *a++;
  a = suffix;
  while (*a)
    name[i++] = *a++;
  copy(name + i, ".txt", 5);
  if (!save(name, bootbuf, (U)n))
    return 0;
  while (n > 0 && (bootbuf[n - 1] == '\n' || bootbuf[n - 1] == '\r'))
    bootbuf[--n] = 0;
  copy(boot, bootbuf, (U)n + 1);
  if (!same(boot, boot_expected))
    return 0;
  procpath(p, "maps");
  n = read_text(p, maps, MAP_CAP);
  if (n < 0)
    return 0;
  *mapsn = (U)n;
  i = 0;
  a = "maps-";
  while (*a)
    name[i++] = *a++;
  a = suffix;
  while (*a)
    name[i++] = *a++;
  copy(name + i, ".txt", 5);
  return save(name, maps, (U)n);
}
static int stat_equal(const struct stat64 *a, const struct stat64 *b) {
  return a->dev == b->dev && a->ino == b->ino && a->mode == b->mode &&
         a->nlink == b->nlink && a->uid == b->uid && a->gid == b->gid &&
         a->rdev == b->rdev && a->size == b->size && a->mtime == b->mtime &&
         a->mtime_ns == b->mtime_ns && a->ctime == b->ctime &&
         a->ctime_ns == b->ctime_ns;
}
static int filecheck(void) {
  struct stat64 pathstat;
  S r = call(80, (U)libfd, (U)&sa, 0, 0, 0, 0);
  if (r < 0) {
    err = -r;
    return 0;
  }
  r = call(79, (U)-100, (U)libpath, (U)&pathstat, 0x100, 0, 0);
  if (r < 0) {
    err = -r;
    return 0;
  }
  return stat_equal(&sb, &sa) && stat_equal(&sb, &pathstat);
}
static int rangehash(char *out, U origin, U size) {
  struct sha s;
  B buf[16384];
  U off = 0;
  sha_init(&s);
  while (off < size) {
    U want = size - off;
    if (want > sizeof buf)
      want = sizeof buf;
    S r = call(67, (U)libfd, (U)buf, want, origin + off, 0, 0);
    if (r != (S)want) {
      err = r < 0 ? -r : 5;
      return 0;
    }
    sha_add(&s, buf, want);
    off += want;
  }
  sha_end(&s, out);
  return 1;
}
static int filehash(char *out) { return rangehash(out, APK_OFFSET, LIB_SIZE); }
static void statfields(const struct stat64 *s, const char *suffix) {
  const char *names[] = {"device", "inode",      "mode",  "size",
                         "mtime",  "mtime_nsec", "ctime", "ctime_nsec"};
  U values[] = {s->dev,      s->ino,      s->mode,     (U)s->size,
                (U)s->mtime, s->mtime_ns, (U)s->ctime, s->ctime_ns};
  for (U i = 0; i < 8; i++) {
    append("library_");
    append(names[i]);
    append(suffix);
    append(" = ");
    uintout(values[i], 10);
    append("\n");
  }
}
__attribute__((noreturn)) static void finish(void) {
  close_fd(memfd);
  close_fd(libfd);
  mn = 0;
  strfield("schema_version", "mho900-lab.private-cache-reader/1");
  strfield("mode", mode);
  strfield("result", accepted ? "accepted" : "rejected");
  strfield("stage", stage);
  numfield("error_number", (U)err);
  numfield("pid", pid);
  numfield("expected_starttime", expected_start);
  numfield("observed_starttime_before",
           start_first ? start_first : observed_start);
  numfield("observed_starttime_after", start_last);
  strfield("expected_boot_id", boot_expected);
  strfield("boot_id_before", boot_first);
  strfield("boot_id_after", boot_last);
  strfield("library_sha256", libhash);
  strfield("backing_apk_sha256", apkhash);
  numfield("embedded_elf_offset", APK_OFFSET);
  numfield("embedded_elf_size", LIB_SIZE);
  strfield(
      "expected_library_sha256",
      same(mode, "wrong-pin")
          ? "0000000000000000000000000000000000000000000000000000000000000000"
          : PIN);
  strfield("library_path", libpath);
  numfield("library_device", sb.dev);
  numfield("library_inode", sb.ino);
  numfield("library_size", (U)sb.size);
  statfields(&sb, "_before");
  statfields(&sa, "_after");
  hexfield("load_bias", bias);
  numfield("maximum_memory_bytes", MAX_TARGET_BYTES);
  numfield("maximum_registry_active", 64);
  numfield("maximum_registry_capacity", 128);
  numfield("window_size", WINDOW);
  numfield("registry_count", owner_count);
  hexfield("registry_address", bias + REGISTRY);
  hexfield("owner_item", owner_item);
  hexfield("owner_base", owner_base);
  hexfield("owner_complete", owner_complete);
  hexfield("working_pointer", work_pointer);
  hexfield("reference_pointer", reference_pointer);
  boolfield("cache_pair_equal", pair_equal);
  boolfield("atomic_snapshot_proven", 0);
  boolfield("physical_fram_read", 0);
  numfield("memory_bytes_requested", requested_bytes);
  numfield("mem_open_flags", 0);
  numfield("mem_open_count", memopens);
  numfield("memory_read_calls", calls);
  numfield("bytes_read", bytes);
  numfield("sample_count", samples);
  boolfield("repeat_equal", repeat_ok);
  boolfield("identity_stable", identity_ok);
  boolfield("maps_stable", maps_ok);
  boolfield("full_maps_changed", full_maps_changed);
  boolfield("file_stable", file_ok);
  strfield("sample_1_sha256", hash1);
  strfield("sample_2_sha256", hash2);
  boolfield("target_attached", 0);
  boolfield("target_calls", 0);
  boolfield("target_writes", 0);
  append("read_addresses = [");
  for (U i=0;i<calls;i++) { if(i)append(", "); uintout(observations[i].address,10); }
  append("]\nread_requested = [");
  for (U i=0;i<calls;i++) { if(i)append(", "); uintout(observations[i].requested,10); }
  append("]\nread_results = [");
  for (U i=0;i<calls;i++) { if(i)append(", "); sintout(observations[i].result); }
  append("]\n");
  for (U i = 0; i < calls; i++) {
    append("\n[[reads]]\n");
    numfield("index", i);
    numfield("round", observations[i].round);
    hexfield("address", observations[i].address);
    numfield("requested", observations[i].requested);
    append("returned = "); sintout(observations[i].result); append("\n");
    boolfield("anonymous", observations[i].anonymous);
    strfield("file", observations[i].name);
  }
  if (outfd >= 0) {
    save("manifest.toml", manifest, mn);
    if (call(82, (U)outfd, 0, 0, 0, 0, 0) < 0)
      evidence_error = 1;
    close_fd(outfd);
  } else
    evidence_error = 1;
  const char *msg = accepted && !evidence_error ? "result = \"accepted\"\n"
                                                : "result = \"rejected\"\n";
  call(64, 1, (U)msg, length(msg), 0, 0, 0);
  call(93, evidence_error ? 4 : (accepted ? 0 : 3), 0, 0, 0, 0, 0);
  __builtin_unreachable();
}
#define REQUIRE(x, s)                                                          \
  do {                                                                         \
    stage = s;                                                                 \
    if (!(x))                                                                  \
      finish();                                                                \
  } while (0)
/* All target reads use one bounded pread path. No target-side methods run. */
static int range_row(const char *maps, U address, U n, int anonymous, struct row *out) {
  if (!n || address > ~0UL - n) return 0;
  const char *p = maps;
  U found = 0;
  while (*p) {
    struct row r;
    if (!row_parse(p, &r)) return 0;
    if (r.lo <= address && address + n <= r.hi) {
      if (found++) return 0;
      if (anonymous) {
        int label = !r.path_n || (r.path_n == 6 && equal(r.path, "[heap]", 6)) ||
          (r.path_n == 18 && equal(r.path, "[anon:libc_malloc]", 18));
        if (!same(r.perm, "rw-p") || r.off || r.maj || r.min || r.ino || !label ||
            !(r.hi <= bias || r.lo >= bias + 0x3cb5000)) return 0;
      } else {
        if (!row_file(&r, libpath, sb.dev, sb.ino) ||
            !(same(r.perm, "r--p") || same(r.perm, "rw-p")) ||
            address < bias + 0xb69c00 || address + n > bias + 0xbe1000) return 0;
      }
      *out = r;
    }
    while (*p && *p != '\n') p++;
    if (*p) p++;
  }
  return found == 1;
}
static int used_maps_equal(void) {
  for (U i = 0; i < calls; i++) {
    struct observation *o = &observations[i];
    struct row a, b;
    if (!range_row(maps0,o->address,o->requested,(int)o->anonymous,&a) ||
        !range_row(maps1,o->address,o->requested,(int)o->anonymous,&b) ||
        a.lo != b.lo || a.hi != b.hi || a.off != b.off || a.maj != b.maj ||
        a.min != b.min || a.ino != b.ino || !same(a.perm,b.perm) ||
        a.path_n != b.path_n || !equal(a.path,b.path,a.path_n)) return 0;
  }
  return 1;
}
static int target_read(U round, U address, B *destination, U n, int anonymous, int metadata_read) {
  struct row mapping;
  stage = "pointer-range";
  if ((address & 7) || !range_row(maps0,address,n,anonymous,&mapping)) return 0;
  stage = "memory-budget";
  if (calls >= MAX_READS || n > MAX_TARGET_BYTES || requested_bytes > MAX_TARGET_BYTES - n ||
      (metadata_read && owner_size[round] + n > sizeof owner[round])) return 0;
  struct observation *o = &observations[calls];
  o->address=address; o->requested=n; o->round=round+1; o->anonymous=(U)anonymous;
  copy(o->name,"read-000.bin",13);
  o->name[5]=(char)('0'+calls/100);o->name[6]=(char)('0'+(calls/10)%10);o->name[7]=(char)('0'+calls%10);
  requested_bytes += n;
  S r = call(67,(U)memfd,(U)destination,n,address,0,0);
  o->result=r; calls++;
  if (r > 0) bytes += (U)r;
  /* Even a short read or error gets an exact raw artifact, without padded bytes. */
  stage = "read-preservation";
  if (!save(o->name,destination,r > 0 ? (U)r : 0)) return 0;
  stage = "memory-read";
  if (r != (S)n) { err = r < 0 ? -r : 5; return 0; }
  if (metadata_read) { copy(owner[round]+owner_size[round],destination,n); owner_size[round]+=n; }
  return 1;
}
static int collect_owner(U round) {
  B registry[24], entries[512], id[8], item[40], setup[160], header[16];
  if (!target_read(round,bias+REGISTRY,registry,24,0,1)) return 0;
  U begin=le(registry,8),end=le(registry+8,8),cap=le(registry+16,8);
  stage="registry-bounds";
  if (!begin || (begin&7) || (end&7) || (cap&7) || end < begin || cap < end ||
      (end-begin)%8 || (cap-begin)%8 || (end-begin)/8 < 1 || (end-begin)/8 > 64 || (cap-begin)/8 > 128) return 0;
  U count=(end-begin)/8;
  struct row capacity_mapping;
  stage="registry-capacity-range";
  if (!range_row(maps0,begin,cap-begin,1,&capacity_mapping)) return 0;
  if (!target_read(round,begin,entries,count*8,1,1)) return 0;
  U selected=0,matches=0;
  for (U i=0;i<count;i++) {
    U address=le(entries+i*8,8);
    if (!target_read(round,address,id,4,1,1)) return 0;
    if (le(id,4)==38) { selected=address; matches++; }
  }
  stage="owner-unique";
  if (matches != 1) return 0;
  if (!target_read(round,selected,item,40,1,1)) return 0;
  U base=le(item+32,8);
  stage="owner-item";
  if (le(item,4)!=38 || base<8 || (base&7)) return 0;
  U complete=base-8;
  if (!target_read(round,complete,setup,160,1,1)) return 0;
  stage="owner-backlink";
  if (le(setup+16,8)!=selected) return 0;
  stage="owner-vtables";
  if (le(setup,8)!=bias+SETUP_VTABLE+16 || le(setup+8,8)!=bias+SETUP_VTABLE+80 ||
      le(setup+72,8)!=bias+SETUP_VTABLE+120) return 0;
  U points[3]={SETUP_VTABLE+16,SETUP_VTABLE+80,SETUP_VTABLE+120};
  U tops[3]={0,(U)-8,(U)-72};
  for (U i=0;i<3;i++) {
    if (!target_read(round,bias+points[i]-16,header,16,0,1)) return 0;
    stage="owner-vtable-headers";
    if (le(header,8)!=tops[i] || le(header+8,8)!=bias+SETUP_TYPEINFO) return 0;
  }
  U working=le(setup+104,8),ref=le(setup+112,8);
  stage="fram-metadata";
  if ((le(setup+88,4)&0x80000000UL) || le(setup+92,4)!=0x50 || le(setup+96,4)!=8192 ||
      !working || !ref || working==ref || (working&7) || (ref&7) ||
      working>~0UL-8192 || ref>~0UL-8192 || !(working+8192<=ref || ref+8192<=working) ||
      !(working+8192<=complete || complete+160<=working) ||
      !(ref+8192<=complete || complete+160<=ref)) return 0;
  struct row wr,rr;
  if (!range_row(maps0,working,8192,1,&wr) || !range_row(maps0,ref,8192,1,&rr)) return 0;
  owner_count=count;owner_item=selected;owner_base=base;owner_complete=complete;
  work_pointer=working;reference_pointer=ref;
  if (!target_read(round,working+256,work[round],WINDOW,1,0) ||
      !target_read(round,ref+256,reference[round],WINDOW,1,0)) return 0;
  /* Conservative full Setup comparison includes mutable ancillary state. Equality
     only brackets these reads; it does not establish an atomic/durable snapshot. */
  B registry_after[24], setup_after[160], item_after[40];
  if (!target_read(round,complete,setup_after,160,1,1) ||
      !target_read(round,selected,item_after,40,1,1) ||
      !target_read(round,bias+REGISTRY,registry_after,24,0,1)) return 0;
  stage="owner-bracket";
  if (!equal(setup,setup_after,160) || !equal(item,item_after,40) ||
      !equal(registry,registry_after,24)) return 0;
  stage="sample-preservation";
  if (!save(round?"owner-2.bin":"owner-1.bin",owner[round],owner_size[round]) ||
      !save(round?"work-2.bin":"work-1.bin",work[round],WINDOW) ||
      !save(round?"ref-2.bin":"ref-1.bin",reference[round],WINDOW)) return 0;
  hash_bytes(owner[round],owner_size[round],round?hash2:hash1);
  return 1;
}

__attribute__((noreturn)) void reader_main(U *stack) {
  U argc = *stack;
  char **argv = (char **)(stack + 1);
  if (argc != 6 && argc != 7)
    finish();
  if (argc == 7)
    mode = argv[6];
  const char *p = argv[1];
  REQUIRE(number(&p, 10, &pid) && !*p && pid > 1, "arguments");
  p = argv[2];
  REQUIRE(number(&p, 10, &expected_start) && !*p && expected_start,
          "arguments");
  boot_expected = argv[3];
  libpath = argv[4];
  outpath = argv[5];
  REQUIRE(length(boot_expected) == 36 && length(libpath) < 512 &&
              libpath[0] == '/' && outpath[0] == '/',
          "arguments");
  REQUIRE(same(mode, "positive") || same(mode, "wrong-pin") ||
              same(mode, "wrong-starttime") || same(mode, "unmapped-range"),
          "arguments");
  S r = call(34, (U)-100, (U)outpath, 0700, 0, 0, 0);
  if (r < 0) {
    err = -r;
    finish();
  }
  outfd = open_path(outpath, 0x4000 | 0x8000 | 0x80000, 0);
  REQUIRE(outfd >= 0, "output-directory");
  if (same(mode, "wrong-starttime")) {
    REQUIRE(expected_start < ~0UL, "arguments");
    expected_start++;
  }
  U n0 = 0, n1 = 0;
  REQUIRE(metadata("before", maps0, &n0, &start_first, boot_first),
          "process-identity");
  REQUIRE(!same(mode, "wrong-starttime"), "negative-control-unexpected-pass");
  libfd = open_path(libpath, 0x8000 | 0x80000, 0);
  if (libfd < 0)
    err = -libfd;
  REQUIRE(libfd >= 0, "library-open");
  r = call(80, (U)libfd, (U)&sb, 0, 0, 0, 0);
  if (r < 0)
    err = -r;
  REQUIRE(r == 0 && (sb.mode & 0170000) == 0100000 && sb.size == APK_SIZE,
          "library-stat");
  copy(&sa, &sb, sizeof sb);
  REQUIRE(rangehash(apkhash, 0, APK_SIZE) && same(apkhash, APK_PIN), "apk-hash");
  REQUIRE(filehash(libhash), "library-hash");
  REQUIRE(same(libhash, same(mode, "wrong-pin")
                            ? "000000000000000000000000000000000000000000000000"
                              "0000000000000000"
                            : PIN),
          "library-hash");
  REQUIRE(!same(mode, "wrong-pin"), "negative-control-unexpected-pass");
  B header[512];
  r = call(67, (U)libfd, (U)header, sizeof header, APK_OFFSET, 0, 0);
  REQUIRE(r == sizeof header && validate_elf(header, sizeof header),
          "library-elf");
  REQUIRE(resolve_maps_ranges(maps0, libpath, sb.dev, sb.ino, &bias,
                              same(mode, "unmapped-range") ? 0 : RAW_BAND, EFFECTIVE_BAND),
          "target-ranges");
  REQUIRE(!same(mode, "unmapped-range"), "negative-control-unexpected-pass");
  REQUIRE(filecheck(), "library-stability");
  char mempath[128];
  procpath(mempath, "mem");
  memfd = open_path(mempath, 0, 0);
  if (memfd < 0)
    err = -memfd;
  else
    memopens++;
  REQUIRE(memfd >= 0, "memory-open");
  U checked_bias = 0;
  REQUIRE(metadata("armed", maps1, &n1, &start_last, boot_last) &&
              resolve_maps(maps1, libpath, sb.dev, sb.ino, &checked_bias) &&
              checked_bias == bias &&
              selected_maps_equal(maps0, maps1, libpath, sb.dev, sb.ino) &&
              filecheck(),
          "armed-stability");
  full_maps_changed = n0 != n1 || !equal(maps0, maps1, n0);
  for (U round = 0; round < 2; round++) {
    REQUIRE(collect_owner(round), stage);
    samples++;
    identity_ok = metadata(round ? "after" : "between", maps1, &n1, &start_last, boot_last);
    REQUIRE(identity_ok, "process-stability");
    full_maps_changed |= n0 != n1 || !equal(maps0, maps1, n0);
    maps_ok = resolve_maps(maps1, libpath, sb.dev, sb.ino, &checked_bias) &&
              checked_bias == bias && selected_maps_equal(maps0, maps1, libpath, sb.dev, sb.ino) && used_maps_equal();
    REQUIRE(maps_ok, "maps-stability");
    file_ok = filecheck();
    REQUIRE(file_ok, "library-stability");
    if (!round) {
      S delay[2] = {0, 100000000};
      r = call(101, (U)delay, 0, 0, 0, 0, 0);
      REQUIRE(r == 0, "sample-interval");
    }
  }
  repeat_ok = owner_size[0] == owner_size[1] && equal(owner[0], owner[1], owner_size[0]) &&
              equal(work[0], work[1], WINDOW) && equal(reference[0], reference[1], WINDOW);
  REQUIRE(repeat_ok, "sample-comparison");
  pair_equal = equal(work[0], reference[0], WINDOW);
  char finalhash[65];
  REQUIRE(filehash(finalhash) && same(finalhash, libhash) && filecheck(),
          "library-final-hash");
  REQUIRE(rangehash(finalhash, 0, APK_SIZE) && same(finalhash, APK_PIN) && filecheck(), "apk-final-hash");
  accepted = 1;
  stage = "complete";
  finish();
}
__asm__(".global _start\n_start:\n mov x0, sp\n bl reader_main\n");
#endif
