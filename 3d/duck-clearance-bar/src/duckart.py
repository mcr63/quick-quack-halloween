"""Flatten the duck from the Quick Quack logo SVG into flat color regions.

Only the duck group is used: the second top-level <g> of the SVG. Its
children are drawn in order. Each shape claims its area and removes that
area from every color drawn before it (painter's algorithm), so the result
is a set of non-overlapping regions, one per fill color.

Output coordinates are SVG units (y down), so callers scale and flip.
"""
import math
import re

import numpy as np
import shapely
from lxml import etree
from shapely.geometry import Polygon
from svgelements import Path as SvgPath, Move, Close, Line

from fontgeom import contours_to_geometry

SVG_NS = '{http://www.w3.org/2000/svg}'

YELLOW = '#FFCF42'
ORANGE = '#F79239'
WHITE = '#FFFFFF'
BLACK = '#000000'


def _flatten_path(d, step):
    """Split an SVG path string into closed polylines (one per subpath)."""
    path = SvgPath(d)
    contours, cur = [], []
    for seg in path:
        if isinstance(seg, Move):
            if len(cur) >= 3:
                contours.append(cur)
            cur = [(seg.end.x, seg.end.y)]
        elif isinstance(seg, Close):
            if len(cur) >= 3:
                contours.append(cur)
            cur = []
        elif isinstance(seg, Line):
            cur.append((seg.end.x, seg.end.y))
        else:
            try:
                length = seg.length(error=1e-3)
            except Exception:
                length = 10.0
            n = max(4, int(math.ceil(length / step)))
            for i in range(1, n + 1):
                p = seg.point(i / n)
                cur.append((p.x, p.y))
    if len(cur) >= 3:
        contours.append(cur)
    return contours


def _parse_matrix(t):
    m = re.match(r'\s*matrix\(([^)]*)\)', t or '')
    if not m:
        return None
    a, b, c, d, e, f = [float(v) for v in re.split(r'[\s,]+', m.group(1).strip())]
    return a, b, c, d, e, f


def _ellipse(el, step):
    cx, cy = float(el.get('cx')), float(el.get('cy'))
    rx, ry = float(el.get('rx')), float(el.get('ry'))
    n = max(64, int(2 * math.pi * max(rx, ry) / step))
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    x = cx + rx * np.cos(t)
    y = cy + ry * np.sin(t)
    mat = _parse_matrix(el.get('transform'))
    if mat:
        a, b, c, d, e, f = mat
        x, y = a * x + c * y + e, b * x + d * y + f
    return Polygon(np.column_stack([x, y]))


def load_duck_shapes(svg_path, step=0.4):
    """Return the duck's drawable shapes in draw order: list of (index, color, geom, tag)."""
    tree = etree.parse(svg_path)
    root = tree.getroot()
    groups = [g for g in root if g.tag == SVG_NS + 'g']
    # The file wraps everything in one outer <g>; inside it the first <g> is
    # the sticker/banner/wordmark and the second <g> is the duck.
    while len(groups) == 1:
        groups = [g for g in groups[0] if g.tag == SVG_NS + 'g']
    duck = groups[1]
    shapes = []
    for i, el in enumerate(duck):
        tag = el.tag.replace(SVG_NS, '')
        if tag == 'line':
            continue  # fill="none" construction line: draws nothing
        fill = (el.get('fill') or BLACK).upper()
        if fill == 'NONE':
            continue
        if tag == 'path':
            geom = contours_to_geometry(_flatten_path(el.get('d'), step))
        elif tag == 'ellipse':
            geom = _ellipse(el, step)
        else:
            continue
        geom = shapely.make_valid(geom).buffer(0)
        shapes.append((i, fill, geom, tag))
    return shapes


def painter_flatten(shapes):
    """Painter's algorithm: later shapes claim their area from earlier colors."""
    regions = {}
    for _, color, geom, _ in shapes:
        for k in list(regions):
            if k != color:
                regions[k] = regions[k].difference(geom)
        regions[color] = regions.get(color, Polygon()).union(geom)
    return {k: v.buffer(0) for k, v in regions.items()}


def split_whites(regions, glint_max_area=60.0):
    """Split the flattened white into the glasses frame and small glints.

    After flattening, the lens rims, bridge and temple arm form one connected
    white frame. The lens glints are small white islands that sit on black.
    Glints are merged into black; the frame is returned separately (it becomes
    bare yellow base, i.e. no raised material).
    """
    white = regions.pop(WHITE, Polygon())
    parts = list(getattr(white, 'geoms', [white]))
    frame = [p for p in parts if p.area >= glint_max_area]
    glints = [p for p in parts if p.area < glint_max_area]
    if glints:
        regions[BLACK] = regions[BLACK].union(shapely.unary_union(glints)).buffer(0)
    return shapely.unary_union(frame) if frame else Polygon(), glints


def duck_regions(svg_path, step=0.4):
    """Flattened duck in SVG units.

    Returns (regions, frame, silhouette, glints): regions maps
    yellow/orange/black to geometry, frame is the white glasses frame, and
    silhouette is the union of every duck shape.
    """
    shapes = load_duck_shapes(svg_path, step)
    regions = painter_flatten(shapes)
    frame, glints = split_whites(regions)
    silhouette = shapely.unary_union([g for _, _, g, _ in shapes]).buffer(0)
    return regions, frame, silhouette, glints
