"""Read Matt's rear-view duck (assets/duck_rear.svg) into flat color regions.

The SVG is four even-odd filled paths drawn in order: the black silhouette
first, then the yellow, orange and white fills on top. So black is the
silhouette minus the other three colors. Output is in SVG units (y down).
"""
import re

import shapely
from lxml import etree
from shapely.geometry import Polygon

SVG_NS = '{http://www.w3.org/2000/svg}'
NAMES = {'#1A1A1A': 'black', '#FDD03F': 'yellow', '#F38E28': 'orange', '#FFFFFF': 'white'}


def _evenodd(d):
    """Polyline path (M/L/Z only) -> polygon with the even-odd fill rule."""
    geom = Polygon()
    for sub in re.split(r'(?=M)', d.strip()):
        nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', sub)]
        pts = list(zip(nums[0::2], nums[1::2]))
        if len(pts) < 3:
            continue
        ring = shapely.make_valid(Polygon(pts)).buffer(0)
        geom = geom.symmetric_difference(ring)
    return geom.buffer(0)


def duck_regions(svg_path):
    """Return (regions, silhouette) in SVG units; regions: yellow, orange, white, black."""
    root = etree.parse(svg_path).getroot()
    shapes = []
    for el in root.iter(SVG_NS + 'path'):
        d = el.get('d')
        if not d or re.search(r'[CcQqAaSsTtHhVv]', d):
            raise ValueError('expected polyline paths only')
        shapes.append((NAMES[el.get('fill').upper()], _evenodd(d)))
    regions = {}
    for color, g in shapes:                      # painter's order
        for k in list(regions):
            if k != color:
                regions[k] = regions[k].difference(g)
        regions[color] = shapely.union(regions.get(color, Polygon()), g)
    sil = shapely.union_all([g for _, g in shapes]).buffer(0)
    regions = {k: v.buffer(0) for k, v in regions.items()}
    return regions, sil
