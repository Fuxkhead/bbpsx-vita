// PS1-style shader pair for vitaGL (Cg, compiled at runtime by libshacccg).
//   vertex:   snaps clip-space vertices to a coarse screen grid (the PS1 "wobble"),
//             and exports the extra interpolants needed for affine texture mapping
//   fragment: texture, alpha cut-out, linear distance fog
// ps1_build() returns 0 on any failure so the caller can fall back to the fixed-function path.
#ifndef PS1SHADER_H
#define PS1SHADER_H
#include <vitaGL.h>
#include <string.h>

static const char *ps1_vert_src =
    "uniform float4x4 wvp;\n"
    "uniform float2 snapHalf;\n"      // half of the snap grid (x,y); 0 disables snapping
    "uniform float2 uvOffset;\n"
    "void main(\n"
    "    float3 aPos,\n"
    "    float2 aUV,\n"
    "    float4 out vPosition : POSITION,\n"
    "    float2 out vUV : TEXCOORD0,\n"
    "    float3 out vAff : TEXCOORD1,\n"
    "    float out vDist : TEXCOORD2\n"
    ") {\n"
    "    float4 p = mul(float4(aPos, 1.0f), wvp);\n"
    "    if (snapHalf.x > 0.0f && p.w > 0.05f) {\n"
    "        float2 ndc = p.xy / p.w;\n"
    "        ndc = floor(ndc * snapHalf + 0.5f) / snapHalf;\n"
    "        p.xy = ndc * p.w;\n"
    "    }\n"
    "    float2 uv = aUV + uvOffset;\n"
    "    vPosition = p;\n"
    "    vUV = uv;\n"
    "    vAff = float3(uv * p.w, p.w);\n"   // vAff.xy / vAff.z = screen-space (affine) interpolated uv
    "    vDist = p.w;\n"
    "}\n";

static const char *ps1_frag_src =
    "uniform sampler2D tex;\n"
    "uniform float4 fogColor;\n"
    "uniform float2 fogRange;\n"       // x = start, y = 1 / (end - start)
    "uniform float affineAmt;\n"
    "uniform float alphaCut;\n"
    "float4 main(\n"
    "    float2 vUV : TEXCOORD0,\n"
    "    float3 vAff : TEXCOORD1,\n"
    "    float vDist : TEXCOORD2\n"
    ") {\n"
    "    float2 uv = lerp(vUV, vAff.xy / vAff.z, affineAmt);\n"
    "    float4 c = tex2D(tex, uv);\n"
    "    if (c.a <= alphaCut) discard;\n"
    "    float f = saturate((vDist - fogRange.x) * fogRange.y);\n"
    "    return float4(lerp(c.rgb, fogColor.rgb, f * (1.0f - fogColor.a)), lerp(1.0f, 1.0f - f, fogColor.a));\n"      // fog_sky: fogColor.a = 1 fades distant things out (the sky behind shows through) instead of colouring them
    "}\n";


// dither_fog: the fog PS1-style: the distance fade is cut into 4 bands and a 4x4 ordered dither (per screen pixel) decides each pixel's band;
// with a sky behind (fogColor.a = 1) distant pixels are simply dropped by the same pattern (screen-door) instead of blended
static const char *ps1_vert_src_d =
    "uniform float4x4 wvp;\n"
    "uniform float2 snapHalf;\n"      // half of the snap grid (x,y); 0 disables snapping
    "uniform float2 uvOffset;\n"
    "void main(\n"
    "    float3 aPos,\n"
    "    float2 aUV,\n"
    "    float4 out vPosition : POSITION,\n"
    "    float2 out vUV : TEXCOORD0,\n"
    "    float3 out vAff : TEXCOORD1,\n"
    "    float out vDist : TEXCOORD2,\n"
    "    float2 out vClip : TEXCOORD3\n"
    ") {\n"
    "    float4 p = mul(float4(aPos, 1.0f), wvp);\n"
    "    if (snapHalf.x > 0.0f && p.w > 0.05f) {\n"
    "        float2 ndc = p.xy / p.w;\n"
    "        ndc = floor(ndc * snapHalf + 0.5f) / snapHalf;\n"
    "        p.xy = ndc * p.w;\n"
    "    }\n"
    "    float2 uv = aUV + uvOffset;\n"
    "    vPosition = p;\n"
    "    vUV = uv;\n"
    "    vAff = float3(uv * p.w, p.w);\n"   // vAff.xy / vAff.z = screen-space (affine) interpolated uv
    "    vDist = p.w;\n"
    "    vClip = p.xy;\n"
    "}\n";

static const char *ps1_frag_src_d =
    "uniform sampler2D tex;\n"
    "uniform float4 fogColor;\n"
    "uniform float2 fogRange;\n"
    "uniform float affineAmt;\n"
    "uniform float alphaCut;\n"
    "float4 main(\n"
    "    float2 vUV : TEXCOORD0,\n"
    "    float3 vAff : TEXCOORD1,\n"
    "    float vDist : TEXCOORD2,\n"
    "    float2 vClip : TEXCOORD3\n"
    ") {\n"
    "    float2 uv = lerp(vUV, vAff.xy / vAff.z, affineAmt);\n"
    "    float4 c = tex2D(tex, uv);\n"
    "    if (c.a <= alphaCut) discard;\n"
    "    float f = saturate((vDist - fogRange.x) * fogRange.y);\n"
    "    if (f <= 0.0f) return float4(c.rgb, 1.0f);\n"
    "    float2 px = floor(vClip / max(vDist, 0.05f) * float2(240.0f, 136.0f));\n"
    "    float2 cc = floor(frac(px * 0.25f) * 4.0f + 0.5f);\n"
    "    float x0 = fmod(cc.x, 2.0f), x1 = floor(cc.x * 0.5f), y0 = fmod(cc.y, 2.0f), y1 = floor(cc.y * 0.5f);\n"
    "    float d = (abs(x0 - y0) * 8.0f + y0 * 4.0f + abs(x1 - y1) * 2.0f + y1 + 0.5f) / 16.0f;\n"
    "    float fq = min(floor(f * 4.0f + d) * 0.25f, 1.0f);\n"
    "    return float4(lerp(c.rgb, fogColor.rgb, fq), 1.0f);\n"
    "}\n";
// tex_dither: PS1 colour depth: every texel is nudged by a 4x4 ordered dither (per screen pixel) and cut to 5 bits per channel; the fog stays smooth
static const char *ps1_frag_src_t =
    "uniform sampler2D tex;\n"
    "uniform float4 fogColor;\n"
    "uniform float2 fogRange;\n"
    "uniform float affineAmt;\n"
    "uniform float alphaCut;\n"
    "float4 main(\n"
    "    float2 vUV : TEXCOORD0,\n"
    "    float3 vAff : TEXCOORD1,\n"
    "    float vDist : TEXCOORD2,\n"
    "    float2 vClip : TEXCOORD3\n"
    ") {\n"
    "    float2 uv = lerp(vUV, vAff.xy / vAff.z, affineAmt);\n"
    "    float4 c = tex2D(tex, uv);\n"
    "    if (c.a <= alphaCut) discard;\n"
    "    float2 px = floor(vClip / max(vDist, 0.05f) * float2(240.0f, 136.0f));\n"
    "    float2 cc = floor(frac(px * 0.25f) * 4.0f + 0.5f);\n"
    "    float x0 = fmod(cc.x, 2.0f), x1 = floor(cc.x * 0.5f), y0 = fmod(cc.y, 2.0f), y1 = floor(cc.y * 0.5f);\n"
    "    float d = (abs(x0 - y0) * 8.0f + y0 * 4.0f + abs(x1 - y1) * 2.0f + y1 + 0.5f) / 16.0f;\n"
    "    float3 q = floor((c.rgb * 255.0f + (d - 0.5f) * 8.0f) / 8.0f) * (8.0f / 255.0f);\n"
    "    q = saturate(q);\n"
    "    float f = saturate((vDist - fogRange.x) * fogRange.y);\n"
    "    return float4(lerp(q, fogColor.rgb, f * (1.0f - fogColor.a)), lerp(1.0f, 1.0f - f, fogColor.a));\n"
    "}\n";
// opaque_fast: for solid textures (no see-through texels, no affine warp): no discard, no affine divide: the cheap path for most of the world
static const char *ps1_frag_src_o =
    "uniform sampler2D tex;\n"
    "uniform float4 fogColor;\n"
    "uniform float2 fogRange;\n"
    "float4 main(\n"
    "    float2 vUV : TEXCOORD0,\n"
    "    float3 vAff : TEXCOORD1,\n"
    "    float vDist : TEXCOORD2\n"
    ") {\n"
    "    float4 c = tex2D(tex, vUV);\n"
    "    float f = saturate((vDist - fogRange.x) * fogRange.y);\n"
    "    return float4(lerp(c.rgb, fogColor.rgb, f * (1.0f - fogColor.a)), lerp(1.0f, 1.0f - f, fogColor.a));\n"
    "}\n";
// opaque_fast + dither_fog: the cheap program for solid textures, with the dithered fog (fog always blends to the fog colour, never to transparent)
static const char *ps1_frag_src_od =
    "uniform sampler2D tex;\n"
    "uniform float4 fogColor;\n"
    "uniform float2 fogRange;\n"
    "float4 main(\n"
    "    float2 vUV : TEXCOORD0,\n"
    "    float3 vAff : TEXCOORD1,\n"
    "    float vDist : TEXCOORD2,\n"
    "    float2 vClip : TEXCOORD3\n"
    ") {\n"
    "    float4 c = tex2D(tex, vUV);\n"
    "    float f = saturate((vDist - fogRange.x) * fogRange.y);\n"
    "    if (f <= 0.0f) return float4(c.rgb, 1.0f);\n"
    "    float2 px = floor(vClip / max(vDist, 0.05f) * float2(240.0f, 136.0f));\n"
    "    float2 cc = floor(frac(px * 0.25f) * 4.0f + 0.5f);\n"
    "    float x0 = fmod(cc.x, 2.0f), x1 = floor(cc.x * 0.5f), y0 = fmod(cc.y, 2.0f), y1 = floor(cc.y * 0.5f);\n"
    "    float d = (abs(x0 - y0) * 8.0f + y0 * 4.0f + abs(x1 - y1) * 2.0f + y1 + 0.5f) / 16.0f;\n"
    "    float fq = min(floor(f * 4.0f + d) * 0.25f, 1.0f);\n"
    "    return float4(lerp(c.rgb, fogColor.rgb, fq), 1.0f);\n"
    "}\n";
static int g_ps1_tdith = 0;
#define PS1_TEX_DITHER 0
static int g_ps1_dith = 0;
#define PS1_DITHER_FOG 1

typedef struct {
    GLuint prog;
    GLint wvp, snapHalf, uvOffset, affineAmt, fogColor, fogRange, alphaCut, tex;
} PS1Shader;

static int ps1_build_src(PS1Shader *s, const char *vsrc, const char *fsrc) {
    memset(s, 0, sizeof(*s));
    GLuint vs = glCreateShader(GL_CG_VERTEX_SHADER_EXT);
    GLuint fs = glCreateShader(GL_CG_FRAGMENT_SHADER_EXT);
    GLint vl = (GLint)strlen(vsrc), fl = (GLint)strlen(fsrc);
    glShaderSource(vs, 1, &vsrc, &vl);
    glCompileShader(vs);
    glShaderSource(fs, 1, &fsrc, &fl);
    glCompileShader(fs);
    GLint ok_v = 0, ok_f = 0;
    glGetShaderiv(vs, GL_COMPILE_STATUS, &ok_v);
    glGetShaderiv(fs, GL_COMPILE_STATUS, &ok_f);
    if (!ok_v || !ok_f) return 0;
    GLuint prog = glCreateProgram();
    glAttachShader(prog, vs);
    glAttachShader(prog, fs);
    glBindAttribLocation(prog, 0, "aPos");
    glBindAttribLocation(prog, 1, "aUV");
    glLinkProgram(prog);
    GLint linked = 0;
    glGetProgramiv(prog, GL_LINK_STATUS, &linked);
    if (!linked) return 0;
    s->prog = prog;
    s->wvp       = glGetUniformLocation(prog, "wvp");
    s->snapHalf  = glGetUniformLocation(prog, "snapHalf");
    s->uvOffset  = glGetUniformLocation(prog, "uvOffset");
    s->affineAmt = glGetUniformLocation(prog, "affineAmt");
    s->fogColor  = glGetUniformLocation(prog, "fogColor");
    s->fogRange  = glGetUniformLocation(prog, "fogRange");
    s->alphaCut  = glGetUniformLocation(prog, "alphaCut");
    s->tex       = glGetUniformLocation(prog, "tex");
    return s->wvp != -1;
}
static int ps1_build(PS1Shader *s) {      // the dithered-fog shader first; if the compiler refuses it, the plain one
    // dither_fog: the dithered shader is kept but switched off (it looked worse than the smooth fog): to try it again set PS1_DITHER_FOG to 1
    if (PS1_DITHER_FOG && ps1_build_src(s, ps1_vert_src_d, ps1_frag_src_d)) { g_ps1_dith = 1; return 1; }
    if (PS1_TEX_DITHER && ps1_build_src(s, ps1_vert_src_d, ps1_frag_src_t)) { g_ps1_tdith = 1; return 1; }
    g_ps1_dith = 0; return ps1_build_src(s, ps1_vert_src, ps1_frag_src);
}
#endif
