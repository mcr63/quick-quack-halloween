"""2D design of the WRONG WAY sign and its pipe saddles.

Coordinates are millimetres, X right, Y up, (0, 0) = lower-left corner of
each part. Every color is a shapely region; raised colors never overlap.
"""
import os
from dataclasses import dataclass

import shapely
import shapely.affinity as aff
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

import duckrear
from fontgeom import Font

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(ROOT, 'fonts')
DUCK_SVG = os.path.join(ROOT, 'assets', 'duck_rear.svg')   # Matt's rear-view duck, walking away
FONT = os.path.join(FONTS, 'Overpass-Bold.ttf')

EMPTY = Polygon()


@dataclass
class Params:
    # sign (MUTCD R5-1a look, 5:3)
    sign_w: float = 240.0
    sign_h: float = 144.0
    radius: float = 12.0
    border_inset: float = 4.0
    border_w: float = 5.0
    sign_line_gap: float = 0.55     # gap between WRONG and WAY, times cap height
    sign_cap_max: float = 40.0      # WRONG / WAY cap height: the largest that fits, up to this
    text_clear: float = 2.5         # text -> border inner edge, at least
    duck_clear: float = 3.0         # duck -> border inner edge (right side)
    duck_h: float = 105.0           # duck height, vertically centered
    text_shift_max: float = 6.0     # text block may move this far up or down from center to fit bigger
    duck_text_gap: float = 3.0      # text -> duck, at least (letters, not outline)
    text_outline: float = 0.8       # black outline around WRONG WAY
    outline_clear: float = 1.0      # orange between the outline and the border or duck, at least
    # printability
    min_stroke: float = 1.0         # text and borders: thinnest raised feature (mm)
    duck_stroke: float = 0.8        # duck black lines and white rims: thinnest (mm)
    duck_min_area: float = 0.5      # drop duck islands smaller than this (mm^2)
    min_gap: float = 0.6            # base gaps between duck lines narrower than this close up


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


def union(*gs):
    gs = [g for g in gs if g is not None and not g.is_empty]
    return unary_union(gs) if gs else EMPTY


def drop_small(g, min_area):
    keep = [p for p in polys(g) if p.area >= min_area]
    out = unary_union(keep) if keep else EMPTY
    return shapely.make_valid(out).buffer(0)


def tidy(g, grid=1e-3):
    """Snap to a 1 um grid so nothing collapses when written at file precision."""
    if g.is_empty:
        return g
    g = shapely.set_precision(shapely.make_valid(g).buffer(0), grid)
    return drop_small(g, 0.01)


def rounded_rect(x0, y0, x1, y1, r):
    if r <= 0:
        return box(x0, y0, x1, y1)
    return box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=32)


def border_ring(w, h, r, inset, bw):
    outer = rounded_rect(inset, inset, w - inset, h - inset, max(r - inset, 0.5))
    inner = rounded_rect(inset + bw, inset + bw, w - inset - bw, h - inset - bw, max(r - inset - bw, 0.5))
    return outer.difference(inner), inner


_fonts = {}


def font(path=FONT):
    if path not in _fonts:
        _fonts[path] = Font(path)
    return _fonts[path]


def text_line(s, cap, path=FONT):
    items, _ = font(path).text(s, cap)
    return union(*[g for _, g, _ in items])


def text_block(lines, cap, gap, cx, cy):
    """Lines stacked on cap-height boxes, each centered on cx; block centered on cy."""
    total = len(lines) * cap + (len(lines) - 1) * gap
    top = cy + total / 2
    out = []
    for i, s in enumerate(lines):
        g = text_line(s, cap)
        b = g.bounds
        base = top - cap - i * (cap + gap)
        out.append(aff.translate(g, cx - (b[0] + b[2]) / 2, base))
    return union(*out)


def min_stroke(geom, lo=0.05, hi=3.0, iters=30):
    """Thinnest stroke: twice the smallest erosion radius that splits or erases a part."""
    n0 = len([q for q in polys(geom) if q.area > 1e-6])
    for _ in range(iters):
        m = (lo + hi) / 2
        n = len([q for q in polys(geom.buffer(-m, quad_segs=32)) if q.area > 1e-6])
        if n == n0:
            lo = m
        else:
            hi = m
    return 2 * lo


def thin_parts(g, stroke):
    """Parts of g that a disk of diameter `stroke` can't reach (corner tips ignored)."""
    r = stroke / 2
    op = g.buffer(-r, quad_segs=16).buffer(r, quad_segs=16)
    lost = g.difference(op.buffer(2e-3))
    out = []
    for q in polys(lost):
        if q.area < 0.02:
            continue
        mrr = q.minimum_rotated_rectangle
        xs, ys = mrr.exterior.coords.xy
        sides = sorted(((xs[k + 1] - xs[k]) ** 2 + (ys[k + 1] - ys[k]) ** 2) ** 0.5 for k in range(4))
        if sides[-1] > 1.2:          # elongated sliver, not a corner trim
            out.append(q)
    return union(*out)


def thicken(g, stroke, limit=None):
    """Grow only the parts thinner than `stroke` until a `stroke` disk fits them."""
    for _ in range(4):
        t = thin_parts(g, stroke)
        if t.is_empty:
            break
        grow = t.buffer(stroke / 2, quad_segs=16)
        if limit is not None:
            grow = grow.intersection(limit)
        g = union(g, grow)
    return g


# ---------------------------------------------------------------- parts

class Sign:
    """WRONG / WAY with the rear-view duck on the right: orange base; yellow border, text
    and duck body; white glasses; black duck linework. The duck's orange (beak, feet)
    is the base showing through."""
    name = 'WRONG WAY sign'

    def __init__(self, p: Params):
        self.p = p
        w, h = p.sign_w, p.sign_h
        self.outline = rounded_rect(0, 0, w, h, p.radius)
        ring, self.opening = border_ring(w, h, p.radius, p.border_inset, p.border_w)
        ob = self.opening.bounds
        duck_h = min(p.duck_h, (ob[3] - ob[1]) - 2 * p.duck_clear)
        self.duck = duck = duck_on_sign(p, duck_h, x_right=ob[2] - p.duck_clear, cy=h / 2)
        self.text, self.cap = self._fit_text(duck['sil'])
        # fill hairline cracks where glyph strokes meet (inside W and N) so the outline
        # only runs around the outside of each letter
        self.text = self.text.buffer(0.15, join_style='mitre', mitre_limit=5).buffer(-0.15, join_style='mitre', mitre_limit=5)
        self.border = ring
        self.text_outline = self._outline(self.text)
        yellow = union(ring, self.text, duck['yellow'])
        black = union(duck['black'], self.text_outline)
        self.colors = {'orange': tidy(self.outline), 'yellow': tidy(yellow),
                       'white': tidy(duck['white']), 'black': tidy(black)}
        self.colors = {k: v for k, v in self.colors.items() if not v.is_empty}
        self.base = 'orange'

    def _outline(self, text):
        """Black ring text_outline wide around the letters (round joins). Orange left between
        outlines or inside counters narrower than text_outline is filled black."""
        p = self.p
        o = p.text_outline
        ring = text.buffer(o, quad_segs=16, join_style='round').difference(text)
        ink = union(text, ring)
        closed = ink.buffer(o / 2, quad_segs=16).buffer(-o / 2, quad_segs=16)
        ring = union(ring, closed.difference(ink.buffer(1e-4)))
        return drop_small(ring.difference(text.buffer(1e-4)), 0.05)

    def _fit_text(self, duck_sil):
        """Largest WRONG / WAY that fits left of the duck, as close to centered as it can be."""
        p = self.p
        edge = max(p.text_clear, p.text_outline + p.outline_clear)
        gap = max(p.duck_text_gap, p.text_outline + p.outline_clear)
        allowed = self.opening.buffer(-edge).difference(duck_sil.buffer(gap, quad_segs=16))
        ab = allowed.bounds
        n = int(p.text_shift_max * 2)
        shifts = sorted((k / 2 for k in range(-n, n + 1)), key=lambda d: (abs(d), -d))
        cap = p.sign_cap_max
        while cap > 10:
            blk = text_block(['WRONG', 'WAY'], cap, p.sign_line_gap * cap, 0.0, p.sign_h / 2)
            bb = blk.bounds
            xs = [x / 4 for x in range(int((ab[0] - bb[0]) * 4), int((ab[2] - bb[2]) * 4) + 1)]
            for dy in shifts:     # closest to centered first
                ok = [x for x in xs if aff.translate(blk, x, dy).within(allowed)]
                if ok:
                    # center left-right in the free space: middle of the feasible shifts
                    self.text_shift = dy
                    return aff.translate(blk, (min(ok) + max(ok)) / 2, dy), cap
            cap -= 0.25
        raise RuntimeError('text does not fit')


def duck_on_sign(p: Params, duck_h, x_right, cy):
    """Matt's rear-view duck, duck_h tall, right edge at x_right, centered on cy.
    Black = silhouette minus the fills. Black lines and white rims thinner than
    duck_stroke are thickened (inside the silhouette); yellow slivers and base gaps
    too thin to print join the black; black specks under duck_min_area are dropped."""
    regions, sil = duckrear.duck_regions(DUCK_SVG)
    b = sil.bounds
    s = duck_h / (b[3] - b[1])

    def place(g):
        g = aff.translate(g, -b[2], -(b[1] + b[3]) / 2)
        g = aff.scale(g, s, -s, origin=(0, 0))       # SVG is y-down
        return aff.translate(g, x_right, cy)

    sil = place(sil)
    yellow, orange, white = (place(regions[c]) for c in ('yellow', 'orange', 'white'))
    st, ma = p.duck_stroke, p.duck_min_area
    white = drop_small(thicken(white, st, limit=sil), ma)
    yellow = yellow.difference(white)
    orange = orange.difference(union(white, yellow))
    for _ in range(4):
        black = sil.difference(union(yellow, orange, white).buffer(1e-4))
        # thin yellow (raised) and thin orange gaps (base) become black
        black = union(black, thin_parts(yellow, st), thin_parts(orange, p.min_gap))
        black = thicken(black, st, limit=sil)
        black = drop_small(black, ma)
        yellow = drop_small(yellow.difference(black), ma)
        orange = orange.difference(black)
        white = drop_small(white.difference(black), ma)
        white = drop_small(thicken(white, st, limit=sil), ma)      # white rims win over black
        black = drop_small(black.difference(white.buffer(1e-4)), ma)
        if thin_parts(black, st).area < 0.05 and thin_parts(white, st).area < 0.05 and thin_parts(yellow, st).area < 0.05:
            break
    return dict(sil=sil, black=black, yellow=yellow, white=white, orange=orange, scale=s)


@dataclass
class MountParams:
    """Snap-on mount for 1 in Sch 40 PVC (OD 33.4 mm): 4 receivers glued to the sign
    back and 2 C clips whose square pegs push into them."""
    pipe_od: float = 33.4
    # receiver
    rec_w: float = 30.0          # footprint, square
    pocket: float = 20.3         # square pocket
    pocket_depth: float = 12.0
    rec_floor: float = 2.0       # glue face -> pocket floor
    mouth_chamfer: float = 0.8
    # positions on the sign back, mm from the sign center (x right as seen from the front, y up)
    rec_pos: tuple = ((0.0, 40.0), (0.0, -40.0), (-70.0, 0.0), (70.0, 0.0))
    rec_names: tuple = ('top', 'bottom', 'left', 'right')
    # clip (2D profile, extruded clip_w)
    bore: float = 33.8
    wall: float = 3.0
    mouth: float = 29.5          # opening at the bore
    flare: float = 2.5           # lead-in: mouth widens 45 deg over this height
    tip_round: float = 0.6
    stem: float = 4.0            # ring -> peg
    stem_fillet: float = 3.0
    peg: float = 20.0            # square peg (profile width x extrusion)
    peg_len: float = 12.0
    clip_w: float = 20.0         # extrusion = width along the pipe

    @property
    def rec_h(self):
        return self.rec_floor + self.pocket_depth

    @property
    def r_in(self):
        return self.bore / 2

    @property
    def r_out(self):
        return self.bore / 2 + self.wall

    @property
    def pipe_center(self):
        """Pipe axis distance from the sign back once the peg is fully in the pocket."""
        return self.rec_floor + self.peg_len + self.stem + self.r_out


def clip_profile(mp: MountParams):
    """C clip in its own 2D frame: bore centered at (0, 0), mouth up (+y), stem and peg
    down (-y). Peg end at y = -(r_out + stem + peg_len)."""
    from shapely.geometry import Point
    ri, ro = mp.r_in, mp.r_out
    ring = Point(0, 0).buffer(ro, quad_segs=64).difference(Point(0, 0).buffer(ri, quad_segs=64))
    hw = mp.mouth / 2
    yi = (ri ** 2 - hw ** 2) ** 0.5                      # where the mouth meets the bore
    top = ro + 5
    cut = Polygon([(-hw, 0), (hw, 0), (hw, yi), (hw + mp.flare, yi + mp.flare), (hw + mp.flare + top, yi + mp.flare + top),
                   (-hw - mp.flare - top, yi + mp.flare + top), (-hw - mp.flare, yi + mp.flare), (-hw, yi)])
    c = ring.difference(cut)
    r = mp.tip_round
    c = c.buffer(-r, quad_segs=16).buffer(r, quad_segs=16)          # round the arm tips
    y0 = -(ro + mp.stem)
    stem = box(-mp.peg / 2, y0, mp.peg / 2, -ri + 0.5)
    body = union(c, stem)
    f = mp.stem_fillet                                                # fillet where stem meets ring
    body = body.buffer(f, quad_segs=16).buffer(-f, quad_segs=16)
    body = body.difference(Point(0, 0).buffer(ri, quad_segs=64)).difference(cut)
    peg = box(-mp.peg / 2, y0 - mp.peg_len, mp.peg / 2, y0 + 0.01)
    out = union(body, peg)
    return max(polys(out), key=lambda q: q.area)
