// Coverage-preserving mip chain for cut-out (alpha-tested) textures.
// Plain box-filtering makes thin features (ladder rails, fences) fade below the alpha
// threshold in smaller mips, so they vanish at a distance. After each downsample the alpha
// is rescaled so the same fraction of texels still passes the alpha test as at level 0.
#ifndef MIPGEN_H
#define MIPGEN_H
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define MIP_ALPHA_REF 85            /* GL_GREATER 0.33 -> alpha >= 85 passes */

static inline float mip_coverage(const uint8_t *p, int n, float scale) {
    int pass = 0;
    for (int i = 0; i < n; i++) { float a = p[i * 4 + 3] * scale; if (a > 255.f) a = 255.f; if (a >= MIP_ALPHA_REF) pass++; }
    return n ? (float)pass / (float)n : 0.f;
}

static inline int mip_has_cutout(const uint8_t *p, int n) {
    for (int i = 0; i < n; i++) if (p[i * 4 + 3] < 255) return 1;
    return 0;
}

// Downsample src (w x h) to (w/2 x h/2) into dst; w and h must be >= 2 and even-or-1 handled by clamping.
// target = desired coverage (0..1). Returns new size via nw/nh.
static inline void mip_next(const uint8_t *src, int w, int h, uint8_t *dst, int *nw, int *nh, float target) {
    int w2 = w > 1 ? w / 2 : 1, h2 = h > 1 ? h / 2 : 1;
    for (int y = 0; y < h2; y++) for (int x = 0; x < w2; x++) {
        float r = 0, g = 0, b = 0, a = 0, wsum = 0;
        for (int dy = 0; dy < 2; dy++) for (int dx = 0; dx < 2; dx++) {
            int sx = x * 2 + dx, sy = y * 2 + dy; if (sx >= w) sx = w - 1; if (sy >= h) sy = h - 1;
            const uint8_t *s = src + ((size_t)sy * w + sx) * 4;
            float sa = s[3];
            r += s[0] * sa; g += s[1] * sa; b += s[2] * sa; a += sa; wsum += sa;
        }
        uint8_t *d = dst + ((size_t)y * w2 + x) * 4;
        if (wsum > 0.f) { d[0] = (uint8_t)(r / wsum + 0.5f); d[1] = (uint8_t)(g / wsum + 0.5f); d[2] = (uint8_t)(b / wsum + 0.5f); }
        else { d[0] = d[1] = d[2] = 0; }
        d[3] = (uint8_t)(a / 4.f + 0.5f);
    }
    // rescale alpha so coverage matches the level-0 coverage
    int n = w2 * h2;
    float lo = 1.f, hi = 8.f;
    if (mip_coverage(dst, n, 1.f) >= target) hi = lo;
    else for (int it = 0; it < 12; it++) { float mid = 0.5f * (lo + hi); if (mip_coverage(dst, n, mid) >= target) hi = mid; else lo = mid; }
    if (hi > 1.f) for (int i = 0; i < n; i++) { float a = dst[i * 4 + 3] * hi; dst[i * 4 + 3] = a > 255.f ? 255 : (uint8_t)(a + 0.5f); }
    *nw = w2; *nh = h2;
}
#endif
