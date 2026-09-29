/* Fixed stock-library cached-data reader. No attachment, target calls or
 * fallback. Linux AArch64 UAPI layout provenance is recorded in inputs.toml. */
typedef unsigned long U;
typedef long S;
typedef unsigned int W;
typedef unsigned char B;
#define PIN "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e"
#define DNA 0xbbccf0UL
#define KEYS 0xbbcd1cUL
#define LIB_SIZE 12453760UL
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
static int resolve_maps_ranges(const char *text, const char *path, U dev, U ino,
                               U *bias, U dna_va, U keys_va) {
  U found = 0, b = 0, previous_end = 0;
  const char *p = text;
  while (*p) {
    struct row r;
    if (!row_parse(p, &r) || r.lo < previous_end)
      return 0;
    previous_end = r.hi;
    if (row_file(&r, path, dev, ino) && r.off == 0 && same(r.perm, "r-xp")) {
      if (found++)
        return 0;
      b = r.lo;
    }
    while (*p && *p != '\n')
      p++;
    if (*p)
      p++;
  }
  if (found != 1 || b > ~0UL - 0x3cb5000)
    return 0;
  U dna = 0, keys = 0, count = 0;
  p = text;
  while (*p) {
    struct row r;
    if (!row_parse(p, &r))
      return 0;
    int identity =
        r.ino == ino &&
        r.maj == (((dev >> 8) & 0xfff) | ((dev >> 32) & 0xfffff000)) &&
        r.min == ((dev & 255) | ((dev >> 12) & 0xffffff00));
    int named = r.path_n == length(path) && equal(r.path, path, r.path_n);
    if (identity || named) {
      if (!row_file(&r, path, dev, ino) || r.perm[0] != 'r' || r.perm[3] != 'p')
        return 0;
      U size = r.hi - r.lo;
      /* PT_LOAD page geometry: data VAs are file offsets plus 0x1000.
       * Anchor bias in the executable offset-zero row, then validate every
       * same-inode/path row, including the split RELRO mapping. */
      int rx = r.off < 0xb69000 && size <= 0xb69000 - r.off &&
               r.lo == b + r.off && r.perm[1] == '-' &&
               (r.perm[2] == 'x' || r.perm[2] == '-');
      int rw = r.off >= 0xb68000 && r.off < 0xbe0000 &&
               size <= 0xbe0000 - r.off && r.lo == b + r.off + 4096 &&
               r.perm[2] == '-' && (r.perm[1] == 'w' || r.perm[1] == '-');
      if (!rx && !rw)
        return 0;
      count++;
      if (rw && same(r.perm, "rw-p")) {
        if (b + dna_va >= r.lo && b + dna_va + 8 <= r.hi &&
            r.off + b + dna_va - r.lo == 0xbbbcf0)
          dna++;
        if (b + keys_va >= r.lo && b + keys_va + 16 <= r.hi &&
            r.off + b + keys_va - r.lo == 0xbbbd1c)
          keys++;
      }
    }
    while (*p && *p != '\n')
      p++;
    if (*p)
      p++;
  }
  if (count < 2 || dna != 1 || keys != 1)
    return 0;
  *bias = b;
  return 1;
}

static int resolve_maps(const char *text, const char *path, U dev, U ino,
                        U *bias) {
  return resolve_maps_ranges(text, path, dev, ino, bias, DNA, KEYS);
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
    manifest[16384];
static U mn, pid, expected_start, observed_start, bias, bytes, calls, memopens,
    samples, requested_bytes;
static S err, reads[4];
static const char *stage = "arguments", *mode = "positive", *libpath, *outpath,
                  *boot_expected;
static int accepted, repeat_ok, identity_ok, maps_ok, file_ok, evidence_error,
    full_maps_changed;
static S outfd = -1, libfd = -1, memfd = -1;
static char libhash[65], hash1[65], hash2[65], boot_first[128], boot_last[128];
static struct stat64 sb, sa;
static U start_first, start_last;
static B sample[2][24];
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
static int filehash(char *out) {
  struct sha s;
  B buf[16384];
  U off = 0;
  sha_init(&s);
  while (off < LIB_SIZE) {
    U want = LIB_SIZE - off;
    if (want > sizeof buf)
      want = sizeof buf;
    S r = call(67, (U)libfd, (U)buf, want, off, 0, 0);
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
  strfield("schema_version", "mho900-lab.cached-identity-reader/1");
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
  strfield(
      "expected_library_sha256",
      same(mode, "wrong-pin")
          ? "0000000000000000000000000000000000000000000000000000000000000000"
          : PIN);
  hexfield("validation_dna_virtual_address",
           same(mode, "unmapped-range") ? 0 : DNA);
  strfield("library_path", libpath);
  numfield("library_device", sb.dev);
  numfield("library_inode", sb.ino);
  numfield("library_size", (U)sb.size);
  statfields(&sb, "_before");
  statfields(&sa, "_after");
  hexfield("load_bias", bias);
  hexfield("dna_address", bias + DNA);
  hexfield("file_keys_address", bias + KEYS);
  numfield("dna_size", 8);
  numfield("file_keys_size", 16);
  numfield("maximum_memory_bytes", 48);
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
  append("read_requested = [");
  for (U i = 0; i < calls; i++) {
    if (i)
      append(", ");
    uintout(i % 2 ? 16 : 8, 10);
  }
  append("]\nread_results = [");
  for (U i = 0; i < calls; i++) {
    if (i)
      append(", ");
    sintout(reads[i]);
  }
  append("]\n");
  boolfield("target_attached", 0);
  boolfield("target_calls", 0);
  boolfield("target_writes", 0);
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
  REQUIRE(r == 0 && (sb.mode & 0170000) == 0100000 && sb.size == LIB_SIZE,
          "library-stat");
  copy(&sa, &sb, sizeof sb);
  REQUIRE(filehash(libhash), "library-hash");
  REQUIRE(same(libhash, same(mode, "wrong-pin")
                            ? "000000000000000000000000000000000000000000000000"
                              "0000000000000000"
                            : PIN),
          "library-hash");
  REQUIRE(!same(mode, "wrong-pin"), "negative-control-unexpected-pass");
  B header[512];
  r = call(67, (U)libfd, (U)header, sizeof header, 0, 0, 0);
  REQUIRE(r == sizeof header && validate_elf(header, sizeof header),
          "library-elf");
  REQUIRE(resolve_maps_ranges(maps0, libpath, sb.dev, sb.ino, &bias,
                              same(mode, "unmapped-range") ? 0 : DNA, KEYS),
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
    U sizes[2] = {8, 16}, offsets[2] = {DNA, KEYS};
    for (U i = 0; i < 2; i++) {
      requested_bytes += sizes[i];
      r = call(67, (U)memfd, (U)(sample[round] + (i ? 8 : 0)), sizes[i],
               bias + offsets[i], 0, 0);
      reads[calls++] = r;
      if (r > 0)
        bytes += (U)r;
      if (r != (S)sizes[i]) {
        if (r < 0)
          err = -r;
        else
          err = 5;
        stage = "memory-read";
        if (bytes)
          save(round ? "sample-2.partial" : "sample-1.partial", sample[round],
               i ? 8 + (r > 0 ? (U)r : 0) : (r > 0 ? (U)r : 0));
        finish();
      }
    }
    samples++;
    hash_bytes(sample[round], 24, round ? hash2 : hash1);
    REQUIRE(save(round ? "sample-2.bin" : "sample-1.bin", sample[round], 24),
            "sample-preservation");
    identity_ok = metadata(round ? "after" : "between", maps1, &n1, &start_last,
                           boot_last);
    REQUIRE(identity_ok, "process-stability");
    full_maps_changed |= n0 != n1 || !equal(maps0, maps1, n0);
    maps_ok = resolve_maps(maps1, libpath, sb.dev, sb.ino, &checked_bias) &&
              checked_bias == bias &&
              selected_maps_equal(maps0, maps1, libpath, sb.dev, sb.ino);
    REQUIRE(maps_ok, "maps-stability");
    file_ok = filecheck();
    REQUIRE(file_ok, "library-stability");
    if (!round) {
      S delay[2] = {0, 100000000};
      r = call(101, (U)delay, 0, 0, 0, 0, 0);
      REQUIRE(r == 0, "sample-interval");
    }
  }
  repeat_ok = equal(sample[0], sample[1], 24);
  REQUIRE(repeat_ok, "sample-comparison");
  char finalhash[65];
  REQUIRE(filehash(finalhash) && same(finalhash, libhash) && filecheck(),
          "library-final-hash");
  accepted = 1;
  stage = "complete";
  finish();
}
__asm__(".global _start\n_start:\n mov x0, sp\n bl reader_main\n");
#endif
