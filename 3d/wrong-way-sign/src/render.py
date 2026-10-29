"""Rasterize shapely geometry into images (used for previews and checks)."""
import numpy as np
from PIL import Image, ImageDraw


def _polys(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    if hasattr(g, 'geoms'):
        out = []
        for x in g.geoms:
            out.extend(_polys(x))
        return out
    return []


class Canvas:
    """World (mm, y up) -> image (px, y down) raster canvas."""

    def __init__(self, xmin, ymin, xmax, ymax, px_per_mm, bg=(255, 255, 255)):
        self.xmin, self.ymin, self.xmax, self.ymax = xmin, ymin, xmax, ymax
        self.k = px_per_mm
        self.w = int(round((xmax - xmin) * px_per_mm))
        self.h = int(round((ymax - ymin) * px_per_mm))
        self.img = Image.new('RGB', (self.w, self.h), bg)

    def to_px(self, coords):
        a = np.asarray(coords, dtype=float)
        x = (a[:, 0] - self.xmin) * self.k
        y = (self.ymax - a[:, 1]) * self.k
        return list(zip(x.tolist(), y.tolist()))

    def mask(self, geom):
        m = Image.new('L', (self.w, self.h), 0)
        for p in _polys(geom):
            pm = Image.new('L', (self.w, self.h), 0)
            d = ImageDraw.Draw(pm)
            d.polygon(self.to_px(p.exterior.coords), fill=255)
            for r in p.interiors:
                d.polygon(self.to_px(r.coords), fill=0)
            m = Image.fromarray(np.maximum(np.asarray(m), np.asarray(pm)))
        return m

    def fill(self, geom, color):
        if geom is None or geom.is_empty:
            return
        # Supersample-free but fast: draw each polygon via its own mask in its bbox.
        for p in _polys(geom):
            x0, y0, x1, y1 = p.bounds
            px0 = max(0, int((x0 - self.xmin) * self.k) - 2)
            px1 = min(self.w, int((x1 - self.xmin) * self.k) + 3)
            py0 = max(0, int((self.ymax - y1) * self.k) - 2)
            py1 = min(self.h, int((self.ymax - y0) * self.k) + 3)
            if px1 <= px0 or py1 <= py0:
                continue
            pm = Image.new('L', (px1 - px0, py1 - py0), 0)
            d = ImageDraw.Draw(pm)
            off = lambda pts: [(x - px0, y - py0) for x, y in self.to_px(pts)]
            d.polygon(off(p.exterior.coords), fill=255)
            for r in p.interiors:
                d.polygon(off(r.coords), fill=0)
            patch = Image.new('RGB', pm.size, color)
            self.img.paste(patch, (px0, py0), pm)

    def line(self, coords, color, width_px=1):
        d = ImageDraw.Draw(self.img)
        d.line(self.to_px(coords), fill=color, width=width_px)

    def outline(self, geom, color, width_px=1):
        d = ImageDraw.Draw(self.img)
        for p in _polys(geom):
            d.line(self.to_px(p.exterior.coords), fill=color, width=width_px)
            for r in p.interiors:
                d.line(self.to_px(r.coords), fill=color, width=width_px)


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
