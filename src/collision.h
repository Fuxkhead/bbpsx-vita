// collision.h - header-only triangle-soup collision + character controller.
// No Vita/GL dependencies, so it can be unit-tested on a PC.
// World: metres, +Z up.
#ifndef COLLISION_H
#define COLLISION_H
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define PL_RADIUS     0.30f
#define PL_EYE        1.60f
#define PL_STEP       0.55f     // max step-up height
static float g_pl_step = PL_STEP;     // the step height in use right now (raised a little at a parked lift so you can board it)
#define PL_GRAVITY    22.0f
#define PL_MAXFALL    40.0f
#define PL_SPHERES    3
static const float PL_SPH_H[PL_SPHERES] = {0.45f, 0.95f, 1.45f};   // sphere centres above feet

typedef struct { float v[9]; } ColTri;

typedef struct {
    ColTri *tris;  int ntris;
    float minx, miny, cell;
    int gw, gh;
    int *cellStart;       // gw*gh+1
    int *items;
    float minz;           // lowest triangle z (fall-out detection)
} ColWorld;

typedef struct {
    float x, y, z;        // feet position
    float vz;
    int   grounded;
} Player;

static int  cw_cellx(const ColWorld *w, float x) { int c = (int)floorf((x - w->minx) / w->cell); return c < 0 ? 0 : (c >= w->gw ? w->gw - 1 : c); }
static int  cw_celly(const ColWorld *w, float y) { int c = (int)floorf((y - w->miny) / w->cell); return c < 0 ? 0 : (c >= w->gh ? w->gh - 1 : c); }

// Takes ownership of `tris` (malloc'd). Returns 1 on success.
static int cw_build(ColWorld *w, ColTri *tris, int n) {
    memset(w, 0, sizeof *w);
    w->tris = tris; w->ntris = n;
    if (n <= 0) return 0;
    float mnx = 1e30f, mny = 1e30f, mxx = -1e30f, mxy = -1e30f, mnz = 1e30f;
    for (int i = 0; i < n; i++)
        for (int k = 0; k < 3; k++) {
            float x = tris[i].v[k*3], y = tris[i].v[k*3+1], z = tris[i].v[k*3+2];
            if (x < mnx) mnx = x; if (x > mxx) mxx = x;
            if (y < mny) mny = y; if (y > mxy) mxy = y;
            if (z < mnz) mnz = z;
        }
    w->minx = mnx; w->miny = mny; w->minz = mnz;
    w->cell = 3.0f;
    while (((mxx - mnx) / w->cell + 1) * ((mxy - mny) / w->cell + 1) > 40000) w->cell *= 2.0f;
    w->gw = (int)((mxx - mnx) / w->cell) + 1;
    w->gh = (int)((mxy - mny) / w->cell) + 1;
    int cells = w->gw * w->gh;
    w->cellStart = (int *)calloc(cells + 1, sizeof(int));
    if (!w->cellStart) return 0;
    for (int pass = 0; pass < 2; pass++) {
        int *fill = NULL;
        if (pass == 1) {
            for (int c = 0; c < cells; c++) w->cellStart[c+1] += w->cellStart[c];
            w->items = (int *)malloc(sizeof(int) * (w->cellStart[cells] ? w->cellStart[cells] : 1));
            fill = (int *)calloc(cells, sizeof(int));
            if (!w->items || !fill) return 0;
        }
        for (int i = 0; i < n; i++) {
            float x0 = 1e30f, y0 = 1e30f, x1 = -1e30f, y1 = -1e30f;
            for (int k = 0; k < 3; k++) {
                float x = tris[i].v[k*3], y = tris[i].v[k*3+1];
                if (x < x0) x0 = x; if (x > x1) x1 = x;
                if (y < y0) y0 = y; if (y > y1) y1 = y;
            }
            int cx0 = cw_cellx(w, x0), cx1 = cw_cellx(w, x1), cy0 = cw_celly(w, y0), cy1 = cw_celly(w, y1);
            for (int cy = cy0; cy <= cy1; cy++)
                for (int cx = cx0; cx <= cx1; cx++) {
                    int c = cy * w->gw + cx;
                    if (pass == 0) w->cellStart[c+1]++;      // count (prefix-summed above)
                    else w->items[w->cellStart[c] + fill[c]++] = i;
                }
        }
        if (fill) free(fill);
    }
    return 1;
}

static void cw_free(ColWorld *w) {
    free(w->tris); free(w->cellStart); free(w->items);
    memset(w, 0, sizeof *w);
}

static void tri_normal(const float *t, float *n) {
    float ux = t[3]-t[0], uy = t[4]-t[1], uz = t[5]-t[2];
    float vx = t[6]-t[0], vy = t[7]-t[1], vz = t[8]-t[2];
    n[0] = uy*vz - uz*vy; n[1] = uz*vx - ux*vz; n[2] = ux*vy - uy*vx;
    float l = sqrtf(n[0]*n[0] + n[1]*n[1] + n[2]*n[2]);
    if (l > 1e-12f) { n[0] /= l; n[1] /= l; n[2] /= l; }
}

// Nearest hit of a ray (origin o, unit direction d, length maxt) against the level, two-sided.
// Used to pull the third-person camera in front of walls. Returns 1 and the distance in *tout on a hit.
static int cw_raycast(const ColWorld *w, const float *o, const float *d, float maxt, float *tout) {
    if (!w->ntris) return 0;
    int hit = 0; float best = maxt;
    float step = w->cell * 0.5f;
    int nsteps = (int)(maxt / step) + 2;
    int lastc = -1;
    for (int s = 0; s <= nsteps; s++) {
        float t = s * step; if (t > maxt) t = maxt;
        int c = cw_celly(w, o[1] + d[1] * t) * w->gw + cw_cellx(w, o[0] + d[0] * t);
        if (c == lastc) { if (t >= maxt) break; continue; }
        lastc = c;
        for (int k = w->cellStart[c]; k < w->cellStart[c+1]; k++) {
            const float *v = w->tris[w->items[k]].v;
            float e1[3] = {v[3]-v[0], v[4]-v[1], v[5]-v[2]}, e2[3] = {v[6]-v[0], v[7]-v[1], v[8]-v[2]};
            float p[3] = {d[1]*e2[2]-d[2]*e2[1], d[2]*e2[0]-d[0]*e2[2], d[0]*e2[1]-d[1]*e2[0]};
            float det = e1[0]*p[0] + e1[1]*p[1] + e1[2]*p[2];
            if (fabsf(det) < 1e-9f) continue;
            float inv = 1.0f / det;
            float tv[3] = {o[0]-v[0], o[1]-v[1], o[2]-v[2]};
            float u = (tv[0]*p[0] + tv[1]*p[1] + tv[2]*p[2]) * inv;
            if (u < 0.0f || u > 1.0f) continue;
            float q[3] = {tv[1]*e1[2]-tv[2]*e1[1], tv[2]*e1[0]-tv[0]*e1[2], tv[0]*e1[1]-tv[1]*e1[0]};
            float vv = (d[0]*q[0] + d[1]*q[1] + d[2]*q[2]) * inv;
            if (vv < 0.0f || u + vv > 1.0f) continue;
            float th = (e2[0]*q[0] + e2[1]*q[1] + e2[2]*q[2]) * inv;
            if (th > 0.0f && th < best) { best = th; hit = 1; }
        }
        if (t >= maxt) break;
    }
    if (hit) *tout = best;
    return hit;
}

// Highest floor-like surface at (x,y) with z <= zmax. Floor-like = |nz| > 0.7
// (we ignore winding, since the level is rendered double-sided). Returns 1 if found.
static int cw_floor_exact(const ColWorld *w, float x, float y, float zmax, float *zout) {
    if (!w->ntris) return 0;
    int c = cw_celly(w, y) * w->gw + cw_cellx(w, x);
    int found = 0; float best = -1e30f;
    for (int k = w->cellStart[c]; k < w->cellStart[c+1]; k++) {
        const float *t = w->tris[w->items[k]].v;
        float n[3]; tri_normal(t, n);
        if (fabsf(n[2]) < 0.7f) continue;
        // barycentric in XY
        float d = (t[4]-t[1])*(t[6]-t[0]) - (t[3]-t[0])*(t[7]-t[1]);
        if (fabsf(d) < 1e-12f) continue;
        float px = x - t[0], py = y - t[1];
        float a = ((t[4]-t[1])*px - (t[3]-t[0])*py) / d;       // weight of vertex 2
        float b = ((t[6]-t[0])*py - (t[7]-t[1])*px) / d;       // weight of vertex 1
        const float e = -2e-3f;
        if (a < e || b < e || a + b > 1.0f - e) continue;
        float z = t[2] + b * (t[5]-t[2]) + a * (t[8]-t[2]);
        if (z <= zmax && z > best) { best = z; found = 1; }
    }
    if (found) *zout = best;
    return found;
}

// Floor lookup that forgives hairline gaps between planks/beams: if the exact spot has no floor, probe a small ring
// around it and use the highest floor found there (so seams between wooden boards don't drop the player through).
static int cw_floor(const ColWorld *w, float x, float y, float zmax, float *zout) {
    if (cw_floor_exact(w, x, y, zmax, zout)) return 1;
    static const float ox[8] = {1, -1, 0, 0, 0.7071f, -0.7071f, 0.7071f, -0.7071f};
    static const float oy[8] = {0, 0, 1, -1, 0.7071f, 0.7071f, -0.7071f, -0.7071f};
    for (int ring = 1; ring <= 3; ring++) {      // gaps between planks: look up to 0.26 m around the feet for a floor
        float r = ring == 3 ? 0.26f : 0.08f * ring, fz, best = -1e30f; int found = 0;
        for (int k = 0; k < 8; k++)
            if (cw_floor_exact(w, x + ox[k] * r, y + oy[k] * r, zmax, &fz) && fz > best) { best = fz; found = 1; }
        if (found) { *zout = best; return 1; }
    }
    return 0;
}

// Closest point on triangle abc to p (Ericson, Real-Time Collision Detection).
static void closest_on_tri(const float *p, const float *t, float *q) {
    const float *a = t, *b = t + 3, *c = t + 6;
    float ab[3] = {b[0]-a[0], b[1]-a[1], b[2]-a[2]};
    float ac[3] = {c[0]-a[0], c[1]-a[1], c[2]-a[2]};
    float ap[3] = {p[0]-a[0], p[1]-a[1], p[2]-a[2]};
#define DOT(u,v) ((u)[0]*(v)[0] + (u)[1]*(v)[1] + (u)[2]*(v)[2])
    float d1 = DOT(ab, ap), d2 = DOT(ac, ap);
    if (d1 <= 0 && d2 <= 0) { memcpy(q, a, 12); return; }
    float bp[3] = {p[0]-b[0], p[1]-b[1], p[2]-b[2]};
    float d3 = DOT(ab, bp), d4 = DOT(ac, bp);
    if (d3 >= 0 && d4 <= d3) { memcpy(q, b, 12); return; }
    float vc = d1*d4 - d3*d2;
    if (vc <= 0 && d1 >= 0 && d3 <= 0) { float v = d1 / (d1 - d3); for (int i = 0; i < 3; i++) q[i] = a[i] + v*ab[i]; return; }
    float cp[3] = {p[0]-c[0], p[1]-c[1], p[2]-c[2]};
    float d5 = DOT(ab, cp), d6 = DOT(ac, cp);
    if (d6 >= 0 && d5 <= d6) { memcpy(q, c, 12); return; }
    float vb = d5*d2 - d1*d6;
    if (vb <= 0 && d2 >= 0 && d6 <= 0) { float v = d2 / (d2 - d6); for (int i = 0; i < 3; i++) q[i] = a[i] + v*ac[i]; return; }
    float va = d3*d6 - d5*d4;
    if (va <= 0 && (d4 - d3) >= 0 && (d5 - d6) >= 0) {
        float v = (d4 - d3) / ((d4 - d3) + (d5 - d6));
        for (int i = 0; i < 3; i++) q[i] = b[i] + v*(c[i]-b[i]); return;
    }
    float den = 1.0f / (va + vb + vc), v = vb * den, ww = vc * den;
    for (int i = 0; i < 3; i++) q[i] = a[i] + ab[i]*v + ac[i]*ww;
#undef DOT
}

// Push the player's body spheres out of wall-like triangles. Returns 1 if anything moved us.
static int cw_push_walls(const ColWorld *w, Player *p) {
    int moved = 0;
    for (int s = 0; s < PL_SPHERES; s++) {
        float c[3] = {p->x, p->y, p->z + PL_SPH_H[s]};
        int cx0 = cw_cellx(w, c[0] - PL_RADIUS), cx1 = cw_cellx(w, c[0] + PL_RADIUS);
        int cy0 = cw_celly(w, c[1] - PL_RADIUS), cy1 = cw_celly(w, c[1] + PL_RADIUS);
        for (int cy = cy0; cy <= cy1; cy++)
            for (int cx = cx0; cx <= cx1; cx++) {
                int cell = cy * w->gw + cx;
                for (int k = w->cellStart[cell]; k < w->cellStart[cell+1]; k++) {
                    const float *t = w->tris[w->items[k]].v;
                    float n[3]; tri_normal(t, n);
                    if (fabsf(n[2]) >= 0.7f && s == 0) continue;     // floors handled by the ground ray
                    if (n[2] > 0.7f) continue;                        // upward-facing floors never push sideways
                    {   // anything lying entirely below step height is a step/curb, not a wall
                        float tmax = t[2] > t[5] ? t[2] : t[5]; if (t[8] > tmax) tmax = t[8];
                        if (tmax <= p->z + g_pl_step) continue;
                    }
                    float q[3]; closest_on_tri(c, t, q);
                    float dx = c[0]-q[0], dy = c[1]-q[1], dz = c[2]-q[2];
                    float d2 = dx*dx + dy*dy + dz*dz;
                    if (d2 >= PL_RADIUS*PL_RADIUS) continue;
                    float d = sqrtf(d2), push;
                    float nx, ny, nz;
                    if (d > 1e-5f) { nx = dx/d; ny = dy/d; nz = dz/d; push = PL_RADIUS - d; }
                    else {         // centre exactly on the surface: use triangle normal facing us
                        nx = n[0]; ny = n[1]; nz = n[2]; push = PL_RADIUS;
                    }
                    // keep the push horizontal unless it's a ceiling-ish contact
                    if (fabsf(nz) < 0.7f) { nz = 0; float l = sqrtf(nx*nx + ny*ny); if (l < 1e-5f) continue; nx /= l; ny /= l; }
                    p->x += nx * push; p->y += ny * push; p->z += nz * push;
                    c[0] = p->x; c[1] = p->y; c[2] = p->z + PL_SPH_H[s];
                    moved = 1;
                }
            }
    }
    return moved;
}

// Advance the player: (mx,my) is the desired horizontal displacement this frame, dt in seconds.
static void pl_update(const ColWorld *w, Player *p, float mx, float my, float dt) {
    // horizontal move in small sub-steps so we can't tunnel through thin walls
    float len = sqrtf(mx*mx + my*my);
    int steps = (int)ceilf(len / 0.15f); if (steps < 1) steps = 1;
    for (int i = 0; i < steps; i++) {
        p->x += mx / steps; p->y += my / steps;
        float fz;
        // step up / follow ground first, so risers lower than PL_STEP don't count as walls
        if (cw_floor(w, p->x, p->y, p->z + g_pl_step, &fz) && fz > p->z && p->grounded) p->z = fz;
        for (int it = 0; it < 3; it++) if (!cw_push_walls(w, p)) break;
    }
    // vertical
    float fz;
    if (p->grounded) {
        // stick to the ground when walking down slopes/stairs
        if (cw_floor(w, p->x, p->y, p->z + g_pl_step, &fz) && p->z - fz <= g_pl_step + 0.05f) { p->z = fz; p->vz = 0; }
        else p->grounded = 0;
    }
    if (!p->grounded) {
        p->vz -= PL_GRAVITY * dt; if (p->vz < -PL_MAXFALL) p->vz = -PL_MAXFALL;
        float nz = p->z + p->vz * dt;
        if (cw_floor(w, p->x, p->y, p->z + 0.05f, &fz) && nz <= fz) { p->z = fz; p->vz = 0; p->grounded = 1; }
        else if (p->vz <= 0.0f && cw_floor(w, p->x, p->y, p->z + 0.35f, &fz) && fz > p->z && nz <= fz) { p->z = fz; p->vz = 0; p->grounded = 1; }      // no_fallthrough: a floor a hand's width above the feet (pushed down by a wall, a dodge over a seam) still catches a falling Hunter
        else p->z = nz;
    }
    // head bump
    cw_push_walls(w, p);
}

#endif
