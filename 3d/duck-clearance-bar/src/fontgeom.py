"""Turn TrueType glyph outlines into shapely geometry (mm, y-up).

Outlines are flattened, then filled with the nonzero winding rule. Variable
fonts such as Oswald keep overlapping contours after instancing, so an
even-odd fill would punch holes where strokes overlap.
"""
import math

import shapely
import shapely.affinity
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union


class _FlattenPen(BasePen):
    def __init__(self, glyphset, step):
        super().__init__(glyphset)
        self.step = step  # target segment length in font units
        self.contours = []
        self.cur = []

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _n(self, pts):
        length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        return max(3, int(math.ceil(length / self.step)))

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        n = self._n([p0, p1, p2])
        for i in range(1, n + 1):
            t = i / n
            a = (1 - t) ** 2
            b = 2 * (1 - t) * t
            c = t * t
            self.cur.append((a * p0[0] + b * p1[0] + c * p2[0],
                             a * p0[1] + b * p1[1] + c * p2[1]))

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        n = self._n([p0, p1, p2, p3])
        for i in range(1, n + 1):
            t = i / n
            a = (1 - t) ** 3
            b = 3 * (1 - t) ** 2 * t
            c = 3 * (1 - t) * t * t
            d = t ** 3
            self.cur.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                             a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))

    def _closePath(self):
        if len(self.cur) >= 3:
            self.contours.append(self.cur)
        self.cur = []

    _endPath = _closePath


def _signed_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2


def _winding_number(pt, ring):
    """Winding number of closed polyline `ring` around point `pt`."""
    x, y = pt
    wn = 0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        if y0 <= y:
            if y1 > y and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) > 0:
                wn += 1
        else:
            if y1 <= y and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) < 0:
                wn -= 1
    return wn


def contours_to_geometry(contours):
    """Fill closed contours with the nonzero winding rule."""
    contours = [c for c in contours if len(c) >= 3 and abs(_signed_area(c)) > 1e-9]
    if not contours:
        return Polygon()
    # Fast path: if no contour boundaries cross, holes are simple.
    lines = [LineString(list(c) + [c[0]]) for c in contours]
    noded = unary_union(lines)
    faces = list(polygonize(noded))
    keep = []
    for f in faces:
        rp = f.representative_point()
        w = sum(_winding_number((rp.x, rp.y), c) for c in contours)
        if w != 0:
            keep.append(f)
    if not keep:
        return Polygon()
    return unary_union(keep).buffer(0)


class Font:
    def __init__(self, path):
        self.tt = TTFont(path)
        self.gs = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()
        self.upm = self.tt['head'].unitsPerEm
        self.cap = getattr(self.tt['OS/2'], 'sCapHeight', 0) or 0.7 * self.upm
        self.hmtx = self.tt['hmtx']
        self.kern = self._read_kern()
        self._cache = {}

    def _read_kern(self):
        """Pair kerning from a GPOS PairPos format-1/2 table (best effort)."""
        pairs = {}
        if 'GPOS' not in self.tt:
            return pairs
        gpos = self.tt['GPOS'].table
        if not gpos.LookupList:
            return pairs
        for lookup in gpos.LookupList.Lookup:
            for st in lookup.SubTable:
                if lookup.LookupType == 9:
                    st = st.ExtSubTable
                if getattr(st, 'LookupType', None) not in (None, 2) and lookup.LookupType not in (2, 9):
                    continue
                if not hasattr(st, 'Format') or not hasattr(st, 'Coverage'):
                    continue
                cov = st.Coverage.glyphs
                if st.Format == 1:
                    for i, g1 in enumerate(cov):
                        ps = st.PairSet[i]
                        for pvr in ps.PairValueRecord:
                            v = getattr(pvr.Value1, 'XAdvance', 0) if pvr.Value1 else 0
                            if v:
                                pairs.setdefault((g1, pvr.SecondGlyph), v)
                elif st.Format == 2:
                    cd1 = st.ClassDef1.classDefs
                    cd2 = st.ClassDef2.classDefs
                    glyphs2 = {}
                    for g, c in cd2.items():
                        glyphs2.setdefault(c, []).append(g)
                    for g1 in cov:
                        c1 = cd1.get(g1, 0)
                        rec = st.Class1Record[c1]
                        for c2, r2 in enumerate(rec.Class2Record):
                            v = getattr(r2.Value1, 'XAdvance', 0) if r2.Value1 else 0
                            if not v or c2 == 0:
                                continue
                            for g2 in glyphs2.get(c2, []):
                                pairs.setdefault((g1, g2), v)
        return pairs

    def glyph_name(self, ch):
        return self.cmap.get(ord(ch))

    def glyph(self, name, step=8.0):
        """Glyph outline in font units as shapely geometry."""
        key = (name, step)
        if key not in self._cache:
            pen = _FlattenPen(self.gs, step)
            self.gs[name].draw(pen)
            self._cache[key] = contours_to_geometry(pen.contours)
        return self._cache[key]

    def advance(self, name):
        return self.hmtx[name][0]

    def text(self, s, size_cap_mm, tracking=0.0, kerning=True, step_mm=0.25):
        """Lay out a string. Returns list of (char, geometry_mm, x_advance_start).

        size_cap_mm: the cap height in mm. tracking is extra space in mm.
        """
        k = size_cap_mm / self.cap
        out = []
        x = 0.0
        prev = None
        for ch in s:
            name = self.glyph_name(ch)
            if name is None:
                raise ValueError(f'glyph missing for {ch!r}')
            if kerning and prev is not None:
                x += self.kern.get((prev, name), 0) * k
            g = self.glyph(name, step=step_mm / k)
            g = shapely.affinity.scale(g, k, k, origin=(0, 0))
            g = shapely.affinity.translate(g, x, 0)
            out.append((ch, g, x))
            x += self.advance(name) * k + tracking
            prev = name
        return out, x
