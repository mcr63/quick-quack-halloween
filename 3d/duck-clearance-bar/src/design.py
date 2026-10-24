"""2D design of the DUCK! CLEARANCE sign.

Coordinates are millimetres, X along the sign (0 = left end), Y up
(0 = bottom edge). Every color is built as a shapely region over the whole
sign, then split into three pieces at two dovetail seams.
"""
import math
import os
import re
from dataclasses import dataclass, field

import shapely
import shapely.affinity as aff
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import duckart
from fontgeom import Font

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(ROOT, 'fonts')
DUCK_SVG = os.path.join(ROOT, 'assets', 'duck_logo.svg')   # Quick Quack logo SVG (only the duck is used)

EMPTY = Polygon()


@dataclass
class Params:
    clearance: str = "6'-7\""          # text after CLEARANCE
    c: float = 26.0                    # CLEARANCE cap height (mm), 41.6% of the face
    H: float = 70.0                    # sign height incl. bars
    top_bar: float = 2.5
    bot_bar: float = 5.0
    # proportions (multiples of c)
    clearance_w: float = 5.6
    word_gap: float = 0.5
    number_w: float = 2.3
    duck_letter_h: float = 1.4
    duck_head_w: float = 2.25
    arrows_w: float = 3.1
    arrow_w: float = 0.9
    arrow_h: float = 1.15
    stripe_w_top: float = 3.5
    stripe_to_arrows: float = -0.27    # stripe field top edge start minus last arrow right edge
    # DUCK! word
    duck_angle: float = 9.0            # degrees CCW
    duck_tracking: float = -1.0        # mm between letters
    duck_x0: float = 43.0              # left edge of the rotated word
    duck_ymin: float = 7.5             # bottom of the rotated word (>= bar + 2)
    halo: float = 2.5                  # yellow halo around DUCK!
    # duck art
    duck_clip_svg_y: float = 330.0     # SVG y that lands on the top edge of the bottom bar
    duck_gap_to_word: float = 3.6      # min distance duck raised art <-> DUCK! green
    # hanging holes
    hole_d: float = 4.5
    ring_d: float = 9.0
    hole_from_end: float = 11.0
    hole_from_top: float = 9.0
    # seams
    edge_keepout: float = 2.0
    dt_neck: float = 14.0
    dt_head: float = 20.0
    dt_depth: float = 9.0
    dt_clear: float = 0.15
    dt_radius: float = 1.0
    # printability
    min_feature: float = 0.45          # drop anything thinner
    min_area: float = 0.5              # drop islands smaller than this (mm^2)
    min_gap_black: float = 0.6         # close black-black gaps narrower than this
    x_stretch: float = 1.08            # horizontal stretch of Bebas Neue

    @property
    def face_y0(self):
        return self.bot_bar

    @property
    def face_y1(self):
        return self.H - self.top_bar

    @property
    def face_cy(self):
        return (self.face_y0 + self.face_y1) / 2


# ---------------------------------------------------------------- helpers

def polys(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    out = []
    for x in getattr(g, 'geoms', []):
        out.extend(polys(x))
    return out


def clean(g, min_feature=0.45, min_area=0.5):
    """Drop parts thinner than min_feature and islands smaller than min_area.

    Morphological opening with a disk (round joins): the result is always a
    subset of the input, so cleaning never makes colors overlap.
    """
    if g is None or g.is_empty:
        return EMPTY
    r = min_feature / 2
    g = g.buffer(-r, quad_segs=16).buffer(r, quad_segs=16)
    return drop_small(g, min_area)


def trim(g, min_feature=0.45, min_area=0.5):
    """Remove slivers thinner than min_feature but keep corners sharp.

    Parts that survive a morphological opening are kept, plus anything of the
    original within 1.5 r of them, so corners (down to ~40 degrees) are not
    rounded. Isolated slivers and islands smaller than min_area are dropped.
    """
    if g is None or g.is_empty:
        return EMPTY
    r = min_feature / 2
    op = g.buffer(-r, quad_segs=16).buffer(r, quad_segs=16)
    if op.is_empty:
        return EMPTY
    return drop_small(g.intersection(op.buffer(1.5 * r, quad_segs=16)), min_area)


def drop_small(g, min_area):
    keep = [p for p in polys(g) if p.area >= min_area]
    out = unary_union(keep) if keep else EMPTY
    return shapely.make_valid(out).buffer(0)


GRID = 1e-3   # mm; every final outline vertex sits on this grid


def shrink(g, d=0.002):
    return g.buffer(-d, join_style='mitre', mitre_limit=5.0) if not g.is_empty else g


def depinch(g, notch=0.01, grid=GRID):
    """Snap to a 1 um grid and remove pinch points.

    Boolean cleanup leaves sub-micron vertex pairs that collapse when written
    at file precision. Snap-rounding (GEOS set_precision) merges them while
    keeping the geometry valid. A valid region can still touch itself at a
    single vertex (a pinch); extruded, that becomes a vertical edge shared by
    four faces, so mesh tools that merge coincident vertices call it
    non-manifold. Each pinch gets a tiny notch of radius `notch` mm.
    """
    import numpy as np
    if g.is_empty:
        return g
    for _ in range(6):
        g = shapely.set_precision(shapely.make_valid(g), grid)
        g = drop_small(g, 0.01)
        g = shapely.set_precision(g, grid)
        pts = []
        for p in polys(g):
            for ring in [p.exterior, *p.interiors]:
                pts.append(np.asarray(ring.coords)[:-1])
        if not pts:
            return g
        P = np.vstack(pts)
        key = np.round(P / grid).astype(np.int64)
        _, inv, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
        dup = np.where(counts[inv] > 1)[0]
        if len(dup) == 0:
            return g
        cuts = unary_union([Point(P[i]).buffer(notch, quad_segs=2) for i in dup])
        g = g.difference(cuts)
    return g


def close_gaps(g, gap):
    """Fill gaps (and notches) narrower than `gap` inside one color."""
    if g.is_empty:
        return g
    r = gap / 2
    return g.buffer(r, quad_segs=16).buffer(-r, quad_segs=16)


def union(*gs):
    gs = [g for g in gs if g is not None and not g.is_empty]
    return unary_union(gs) if gs else EMPTY


# ---------------------------------------------------------------- stripes

def stripe_field_left(p: Params, L):
    """Orange '/' stripes at the left end, ending on a diagonal stripe edge."""
    Ws = p.stripe_w_top * p.c
    # photo ratios at the top edge (outer end first): yellow 0.547p, orange 0.544p, gap 0.456p
    per = Ws / (0.547 + 3 * 0.544 + 2 * 0.456)
    o, y0 = 0.544 * per, 0.547 * per
    # the bands run 1 mm into both bars; the bars cut them flat later
    yt, yb = p.face_y1 + 1.0, p.face_y0 - 1.0
    ut = p.face_y1
    bands = []
    for i in range(-6, 3):
        ua = y0 + i * per
        ub = ua + o
        bands.append(Polygon([(ua + yb - ut, yb), (ub + yb - ut, yb), (ub + yt - ut, yt), (ua + yt - ut, yt)]))
    field = union(*bands)
    keep = box(p.edge_keepout, yb, L, yt)
    return field.intersection(keep), Ws


def mirror_x(g, L):
    return aff.scale(g, -1, 1, origin=(L / 2, 0))


# ---------------------------------------------------------------- text

_fonts = {}


def font(name):
    if name not in _fonts:
        path = {
            'lilita': os.path.join(FONTS, 'lilitaone_LilitaOne-Regular.ttf'),
            'bebas': os.path.join(FONTS, 'bebasneue_BebasNeue-Regular.ttf'),
        }[name]
        _fonts[name] = Font(path)
    return _fonts[name]


def text_geom(fontname, s, cap, tracking=0.0, sx=1.0):
    f = font(fontname)
    glyphs, adv = f.text(s, cap, tracking=0.0, kerning=True)
    out = []
    shift = 0.0
    for i, (ch, g, x) in enumerate(glyphs):
        g = aff.scale(g, sx, 1.0, origin=(0, 0))
        g = aff.translate(g, shift, 0)
        out.append((ch, g))
        shift += tracking
    return out


def ink_bounds(items):
    return union(*[g for _, g in items]).bounds


def tick(p: Params, x_left, y_bottom):
    """Slanted prime tick like the photo: wide flat top, narrow foot, leaning right."""
    h = 0.42 * p.c
    pts = [(0, 0), (0.24 * h, 0), (0.57 * h, h), (0.14 * h, h)]
    g = Polygon([(x_left + a, y_bottom + b) for a, b in pts])
    r = 0.35
    return g.buffer(-r).buffer(r)


def tick_metrics(p: Params):
    h = 0.42 * p.c
    return h, 0.57 * h, 0.56 * h   # height, bbox width, pitch for a double tick


def number_geom(p: Params, s, x0, baseline):
    """Lay out the clearance figure, e.g. 6'-7", with drawn ticks and hyphen.

    Returns (geometry, right_x). Gaps follow the photo (in units of c).
    """
    c = p.c
    th, tw, pitch = tick_metrics(p)
    tick_bottom = baseline + c + 0.03 * c - th
    toks = []
    for ch in s:
        if ch in "'′’":
            toks.append(('tick1', None))
        elif ch in '"″”':
            toks.append(('tick2', None))
        elif ch in '-‐‑‒–':
            toks.append(('dash', None))
        elif ch == ' ':
            toks.append(('space', None))
        else:
            toks.append(('glyph', ch))
    # gap before a token, given the previous token kind (photo measurements / c)
    gap_after = {'glyph': {'tick1': 0.114, 'tick2': 0.09, 'dash': 0.06, 'glyph': 0.07},
                 'tick1': {'dash': 0.036, 'glyph': 0.06, 'tick1': 0.06},
                 'tick2': {'glyph': 0.06, 'dash': 0.06},
                 'dash': {'glyph': 0.054, 'tick1': 0.05}}
    x = x0
    parts = []
    prev = None
    for kind, ch in toks:
        if kind == 'space':
            x += 0.25 * c
            prev = None
            continue
        if prev is not None:
            x += gap_after.get(prev, {}).get(kind, 0.07) * c
        if kind == 'glyph':
            items = text_geom('bebas', ch, c, sx=p.x_stretch)
            g = items[0][1]
            b = g.bounds
            g = aff.translate(g, x - b[0], baseline)
            parts.append(g)
            x = g.bounds[2]
        elif kind == 'tick1':
            g = tick(p, x, tick_bottom)
            parts.append(g)
            x = g.bounds[2]
        elif kind == 'tick2':
            g1 = tick(p, x, tick_bottom)
            g2 = tick(p, x + pitch, tick_bottom)
            parts += [g1, g2]
            x = g2.bounds[2]
        elif kind == 'dash':
            w, hh = 0.24 * c, 0.18 * c
            cy = baseline + 0.56 * c
            g = box(x, cy - hh / 2, x + w, cy + hh / 2)
            g = g.buffer(-0.35).buffer(0.35)
            parts.append(g)
            x = g.bounds[2]
        prev = kind
    return union(*parts), x


def clearance_geom(p: Params, x_left, baseline):
    """CLEARANCE in Bebas Neue, stretched and tracked to clearance_w * c wide."""
    c = p.c
    items = text_geom('bebas', 'CLEARANCE', c, sx=p.x_stretch)
    b = ink_bounds(items)
    natural = b[2] - b[0]
    tracking = (p.clearance_w * c - natural) / (len(items) - 1)
    items = text_geom('bebas', 'CLEARANCE', c, tracking=tracking, sx=p.x_stretch)
    g = union(*[x for _, x in items])
    b = g.bounds
    return aff.translate(g, x_left - b[0], baseline), tracking


# ---------------------------------------------------------------- DUCK!

def duck_word(p: Params):
    cap = p.duck_letter_h * p.c
    items = text_geom('lilita', 'DUCK!', cap, tracking=p.duck_tracking)
    letters = [g for _, g in items]
    g = union(*letters)
    g = aff.rotate(g, p.duck_angle, origin=(0, 0))
    b = g.bounds
    dx, dy = p.duck_x0 - b[0], p.duck_ymin - b[1]
    g = aff.translate(g, dx, dy)
    # filled outline (counters filled) for the halo
    filled = union(*[Polygon(q.exterior) for q in polys(g)])
    return g, filled


# ---------------------------------------------------------------- duck art

class DuckArt:
    def __init__(self, p: Params, svg=DUCK_SVG):
        self.p = p
        regions, frame, sil, glints = duckart.duck_regions(svg)
        self.regions_svg = regions
        self.frame_svg = frame
        self.sil_svg = sil
        # head extent (SVG): temple-arm tip to beak tip
        head_win = box(1000, 150, 1300, 345)
        head = sil.intersection(head_win)
        hb = head.bounds
        self.u_min, self.u_max = hb[0], hb[2]
        self.s = p.duck_head_w * p.c / (self.u_max - self.u_min)

    def to_sign(self, g, x0):
        """SVG -> sign: x' = x0 + (u-u_min)*s, y' = face_y0 + (clip - v)*s."""
        s, p = self.s, self.p
        g = aff.translate(g, -self.u_min, -p.duck_clip_svg_y)
        g = aff.scale(g, s, -s, origin=(0, 0))
        return aff.translate(g, x0, p.face_y0)

    def pt(self, u, v, x0):
        s, p = self.s, self.p
        return (x0 + (u - self.u_min) * s, p.face_y0 + (p.duck_clip_svg_y - v) * s)

    def placed(self, x0):
        p = self.p
        # clip 0.6 mm below the bar edge: the bar cuts the art flat later, so
        # cleanup never rounds the corners where the duck meets the bar
        clipbox = box(-1e4, p.face_y0 - 0.6, 1e4, p.face_y1)
        yellow = self.to_sign(self.regions_svg[duckart.YELLOW], x0).intersection(clipbox)
        orange = self.to_sign(self.regions_svg[duckart.ORANGE], x0).intersection(clipbox)
        black = self.to_sign(self.regions_svg[duckart.BLACK], x0).intersection(clipbox)
        frame = self.to_sign(self.frame_svg, x0).intersection(clipbox)
        sil = self.to_sign(self.sil_svg, x0).intersection(clipbox)
        # frame gaps narrower than min_gap_black merge into black
        frame_ok = frame.buffer(-p.min_gap_black / 2).buffer(p.min_gap_black / 2)
        frame_lost = frame.difference(frame_ok.buffer(1e-3))
        black = union(black, frame_lost)
        # close black-black gaps narrower than min_gap_black (wedges against the
        # bottom bar are closed later, once the real bar exists)
        black = drop_small(close_gaps(black, p.min_gap_black).intersection(clipbox), 1e-3)
        return dict(yellow=yellow, orange=orange.difference(black), black=black, frame=frame_ok, sil=sil)


def _top_of(geom, X, H):
    hit = geom.boundary.intersection(LineString([(X, -1), (X, H + 1)]))
    ys = [q.y for q in getattr(hit, 'geoms', [hit]) if not q.is_empty]
    return max(ys) if ys else None


def bump_and_bonk(p: Params, art: DuckArt, x0, duck):
    """Orange bump growing out of the crown, 3 impact lines, Bonk!!!.

    The bump is a disk whose centre sits just inside the head outline. The part
    of the disk outside the head's yellow interior becomes orange (it replaces
    the head outline under it); a black rim outlines the dome outside the head,
    so the outline seems to swell over the bump.
    """
    sil = duck['sil']
    X, _ = art.pt(p_bump_u, 0, x0)
    P = (X, _top_of(sil, X, p.H))
    # outward normal from the silhouette boundary near P, biased upward
    bd = sil.boundary
    d = bd.project(Point(P))
    a, b = bd.interpolate(d - 1.0), bd.interpolate(d + 1.0)
    n = (-(b.y - a.y), b.x - a.x)
    if n[1] < 0:
        n = (-n[0], -n[1])
    n = (n[0], n[1] + 0.55 * math.hypot(*n))
    nl = math.hypot(*n)
    n = (n[0] / nl, n[1] / nl)
    a_, b_, inset, w = 3.9, 4.9, 1.1, 0.95   # half-width, half-height, centre depth, rim
    r = b_
    C = (P[0] - n[0] * inset, P[1] - n[1] * inset)
    D = aff.scale(Point(0, 0).buffer(1.0, 96), a_, b_, origin=(0, 0))
    D = aff.rotate(D, math.degrees(math.atan2(n[1], n[0])) - 90.0, origin=(0, 0))
    D = aff.translate(D, *C)
    head_fill = sil.buffer(-1.7)       # yellow interior inside the head outline
    D_in = D.buffer(-w)
    bump_orange = D_in.difference(head_fill)
    bump_black = D.difference(D_in).difference(head_fill)
    # impact lines fanning out from the dome
    base = math.atan2(n[1], n[0])
    lines = []
    for da, r0, r1 in ((-40.0, 1.5, 5.0), (0.0, 1.5, 5.6), (40.0, 1.5, 5.0)):
        th = base + math.radians(da)
        q0 = (C[0] + (r + r0) * math.cos(th), C[1] + (r + r0) * math.sin(th))
        q1 = (C[0] + (r + r1) * math.cos(th), C[1] + (r + r1) * math.sin(th))
        lines.append(LineString([q0, q1]).buffer(0.55, cap_style='round'))
    impact = union(*lines)
    # Lilita One's k has a 0.78 mm neck at 6.6 mm caps; 7 mm caps plus a
    # 0.1 mm emboldening keeps every stroke >= 1 mm
    cap = 7.0
    items = text_geom('lilita', 'Bonk!!!', cap, tracking=0.25)
    bonk = union(*[g for _, g in items]).buffer(0.1, quad_segs=8)
    return dict(bump_orange=bump_orange, bump_black=bump_black, impact=impact,
                bonk_raw=bonk, crown=P, normal=n, dome=D)


p_bump_u = 1088.0   # SVG x of the crown point that carries the bump


# ---------------------------------------------------------------- arrows

def arrow(p: Params, x_left, y_bottom):
    w, h = p.arrow_w * p.c, p.arrow_h * p.c
    sw = 0.58 * w
    hh = 0.56 * h
    cx = x_left + w / 2
    pts = [(cx - sw / 2, y_bottom + h), (cx + sw / 2, y_bottom + h), (cx + sw / 2, y_bottom + hh),
           (x_left + w, y_bottom + hh), (cx, y_bottom), (x_left, y_bottom + hh),
           (cx - sw / 2, y_bottom + hh)]
    return Polygon(pts)


# ---------------------------------------------------------------- dovetails

def dovetail_tab(p: Params, s, cy):
    """Tab that sticks out to the LEFT of seam line x=s (part of the right piece).

    Includes 1 mm rounds on the head corners and 1 mm root fillets.
    """
    n2, h2, d = p.dt_neck / 2, p.dt_head / 2, p.dt_depth
    r = p.dt_radius
    T = Polygon([(s, cy - n2), (s - d, cy - h2), (s - d, cy + h2), (s, cy + n2)])
    # round the head corners (opening), keep the root sharp by extending into the body
    Tx = union(T, box(s, cy - h2 - 3, s + 6, cy + h2 + 3))
    Tr = Tx.buffer(-r).buffer(r).intersection(box(s - d - 1, cy - h2 - 3, s, cy + h2 + 3))
    # root fillets (closing against a big body proxy), keep only what is left of s
    body = box(s, cy - 40, s + 40, cy + 40)
    closed = union(Tr, body).buffer(r).buffer(-r)
    tab = closed.intersection(box(s - d - 1, cy - h2 - 5, s, cy + h2 + 5))
    return tab.buffer(0)


@dataclass
class Layout:
    p: Params
    L: float = 0.0
    s1: float = 0.0
    s2: float = 0.0
    colors: dict = field(default_factory=dict)     # global raised colors
    bars: object = None
    pieces: list = field(default_factory=list)      # outlines
    piece_names: list = field(default_factory=list)
    tabs: list = field(default_factory=list)
    sockets: list = field(default_factory=list)
    holes: object = None
    info: dict = field(default_factory=dict)


def _min_x_clear(geom, make_keepout, lo, hi, need=2.0, iters=40):
    """Smallest seam x in [lo, hi] whose keep-out stays >= need from geom."""
    def ok(x):
        return geom.distance(make_keepout(x)) >= need - 1e-6
    if not ok(hi):
        raise ValueError('cannot clear geometry')
    for _ in range(iters):
        mid = (lo + hi) / 2
        if ok(mid):
            hi = mid
        else:
            lo = mid
    return hi


def build_layout(p: Params) -> Layout:
    lay = Layout(p)
    c = p.c
    cy_dt = p.H / 2
    face = box(-1e4, p.face_y0, 1e4, p.face_y1)

    # --- DUCK! word
    word, word_filled = duck_word(p)

    # --- duck art: slide it right until it clears the word by duck_gap_to_word
    art = DuckArt(p)
    probe = art.placed(0.0)
    raised0 = union(probe['black'], probe['orange'])
    wb = word.bounds
    lo, hi = wb[2] - 80, wb[2] + 40
    def dist_ok(x0):
        r = aff.translate(raised0, x0, 0)
        return r.distance(word) >= p.duck_gap_to_word
    for _ in range(40):
        mid = (lo + hi) / 2
        if dist_ok(mid):
            hi = mid
        else:
            lo = mid
    x0 = hi
    duck = art.placed(x0)
    bb = bump_and_bonk(p, art, x0, duck)

    # Bonk!!! to the upper right of the bump, just above the head (like the photo)
    duck_raised = union(duck['black'], duck['orange'], bb['bump_black'], bb['impact'])
    bonk = bb['bonk_raw']
    bkb = bonk.bounds
    dome_b = bb['dome'].bounds
    bx = dome_b[2] + 2.0
    bonk = aff.translate(bonk, bx - bkb[0], 0)
    # lowest baseline that keeps 1.5 mm from the duck and its impact lines
    y = duck['sil'].intersection(box(bx - 1, 0, bx + bkb[2] - bkb[0] + 1, p.H)).bounds[3] + 1.5
    bonk = aff.translate(bonk, 0, y - bkb[1])
    while bonk.distance(duck_raised) < 1.5:
        bonk = aff.translate(bonk, 0, 0.2)
    top_limit = p.face_y1 - p.edge_keepout
    if bonk.bounds[3] > top_limit:
        raise ValueError('Bonk!!! does not fit under the top bar')
    lay.info['bonk_bounds'] = bonk.bounds

    duck_black = union(duck['black'], bb['bump_black'], bb['impact'])
    duck_black = duck_black.difference(bb['bump_orange'])
    duck_orange = union(duck['orange'].difference(bb['bump_orange'].buffer(0)), bb['bump_orange'], bonk)
    duck_orange = duck_orange.difference(duck_black)

    # --- seam 1: tab from piece 2 sticks left into a socket in piece 1
    # only what shows above the bottom bar counts (the art runs 0.6 mm under it)
    left_stuff = drop_small(union(word, duck_black, duck_orange).intersection(
        box(-1e4, p.face_y0, 1e4, p.H)), 1e-6)
    def keep1(s):
        tab = dovetail_tab(p, s, cy_dt)
        sock = tab.buffer(p.dt_clear)
        return union(sock, LineString([(s, -1), (s, p.H + 1)]))
    rx = left_stuff.bounds[2]
    s1 = _min_x_clear(left_stuff, keep1, rx, rx + 30, need=p.edge_keepout)

    # --- CLEARANCE + figure
    baseline = p.face_cy - c / 2
    clear_x = s1 + p.edge_keepout + 0.05
    clr, tracking = clearance_geom(p, clear_x, baseline)
    num_x = clr.bounds[2] + p.word_gap * c
    num, num_right = number_geom(p, p.clearance, num_x, baseline)
    lay.info.update(clear_tracking=tracking, clearance_bounds=clr.bounds, number_bounds=num.bounds)

    # --- seam 2: tab from piece 3 sticks left into a socket in piece 2
    def keep2(s):
        tab = dovetail_tab(p, s, cy_dt)
        return union(tab.buffer(p.dt_clear), LineString([(s, -1), (s, p.H + 1)]))
    nb = num.bounds
    s2 = _min_x_clear(num, keep2, nb[2], nb[2] + 30, need=p.edge_keepout)

    # --- arrows
    aw, ah = p.arrow_w * c, p.arrow_h * c
    gap = (p.arrows_w * c - 3 * aw) / 2
    ay = p.face_cy - ah / 2
    ax = s2 + p.edge_keepout + 0.05
    arrows = union(*[arrow(p, ax + i * (aw + gap), ay) for i in range(3)])
    arrows_right = arrows.bounds[2]

    # --- right stripe field and total length
    Ws = p.stripe_w_top * c
    xf = arrows_right + p.stripe_to_arrows * c
    L = xf + Ws
    lay.L, lay.s1, lay.s2 = L, s1, s2

    # --- stripes (orange), halo, rings
    left_field, _ = stripe_field_left(p, L)
    right_field = mirror_x(left_field, L)
    stripes = union(left_field, right_field)
    # sticker-style halo: 2.5 mm offset, cusps between letters smoothed (closing
    # only adds yellow, so the halo is never narrower than p.halo)
    halo = word_filled.buffer(p.halo, quad_segs=24).buffer(2.0, quad_segs=24).buffer(-2.0, quad_segs=24)
    stripes = stripes.difference(halo)
    hy = p.H - p.hole_from_top
    holes_c = [(p.hole_from_end, hy), (L - p.hole_from_end, hy)]
    ring_outer = union(*[Point(q).buffer(p.ring_d / 2, 96) for q in holes_c])
    holes = union(*[Point(q).buffer(p.hole_d / 2, 64) for q in holes_c])
    rings = ring_outer.difference(holes)

    # --- bars
    bars = union(box(0, 0, L, p.bot_bar), box(0, p.H - p.top_bar, L, p.H))

    # --- assemble colors with priority black > green > orange
    black = union(bars, duck_black, clr, num, arrows, rings)
    # close sub-0.6 mm yellow wedges between the duck's outlines and the bottom bar
    db = duck['sil'].bounds
    zone = box(db[0] - 1.0, 0, db[2] + 1.0, p.face_y1)
    black = union(black, close_gaps(black.intersection(zone), p.min_gap_black).intersection(zone))
    green = word.difference(black)
    orange = union(stripes, duck_orange).difference(black).difference(green)

    mf, ma = p.min_feature, p.min_area
    sign = box(0, 0, L, p.H)
    # Rings are exact shapes: keep them out of the trim. The bars stay in so the
    # duck's outlines merge into the bottom bar; exact bars are re-added after.
    black_c = union(trim(black.difference(ring_outer), mf, ma), bars, rings)
    black_c = depinch(black_c.intersection(sign).difference(holes))
    # Priority black > green > orange: each lower colour is cut by the final
    # higher ones, trimmed of slivers, then pulled back 2 um so snapping both
    # outlines to the 1 um grid cannot make them overlap.
    green_c = depinch(shrink(trim(green.difference(black_c), mf, ma)))
    orange_c = depinch(shrink(trim(orange.difference(black_c).difference(green_c), mf, ma)))
    lay.colors = dict(orange=orange_c, green=green_c, black=black_c)
    lay.bars = bars
    lay.holes = holes

    # --- pieces
    tab1 = dovetail_tab(p, s1, cy_dt)
    tab2 = dovetail_tab(p, s2, cy_dt)
    sock1 = tab1.buffer(p.dt_clear)
    sock2 = tab2.buffer(p.dt_clear)
    P1 = box(0, 0, s1, p.H).difference(sock1).difference(holes)
    P2 = union(box(s1, 0, s2, p.H), tab1).difference(sock2)
    P3 = union(box(s2, 0, L, p.H), tab2).difference(holes)
    lay.pieces = [depinch(P1.buffer(0)), depinch(P2.buffer(0)), depinch(P3.buffer(0))]
    lay.piece_names = ['Piece 1 - DUCK', 'Piece 2 - CLEARANCE', 'Piece 3 - arrows']
    lay.tabs = [tab1, tab2]
    lay.sockets = [sock1, sock2]
    lay.info.update(duck_x0=x0, duck_scale=art.s, word_bounds=word.bounds, s1=s1, s2=s2, L=L,
                    arrows_bounds=arrows.bounds, stripe_top_start_right=xf,
                    duck_bounds=union(duck_black, duck['orange']).bounds,
                    crown=bb['crown'])
    lay.parts_raw = dict(word=word, word_filled=word_filled, duck=duck, bb=bb, clr=clr, num=num,
                         arrows=arrows, stripes=stripes, rings=rings, bonk=bonk)
    return lay


def piece_colors(lay: Layout):
    """Per piece: dict color -> region (raised colors clipped to the piece)."""
    out = []
    for P in lay.pieces:
        d = {'yellow': P}
        for k, g in lay.colors.items():
            gi = depinch(drop_small(g.intersection(P), 0.05))
            if not gi.is_empty and gi.area > 0.01:
                d[k] = gi
        out.append(d)
    return out
