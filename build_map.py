"""Genera docs/caldas.json desde OpenStreetMap (ODbL). Manizales no tiene relación propia en OSM:
se obtiene como Caldas menos los otros 26 municipios. Requiere data/osm.json y data/osm_caldas.json (Overpass)."""
import json, shapely
from shapely.geometry import LineString, mapping
from shapely.ops import polygonize, unary_union

def poly(rel):
    outer = [LineString([(p['lon'], p['lat']) for p in m['geometry']]) for m in rel['members'] if m['type'] == 'way' and m['role'] in ('outer', '')]
    inner = [LineString([(p['lon'], p['lat']) for p in m['geometry']]) for m in rel['members'] if m['type'] == 'way' and m['role'] == 'inner']
    g = unary_union(list(polygonize(unary_union(outer))))
    return g.difference(unary_union(list(polygonize(unary_union(inner))))) if inner else g

munis = {e['tags']['name']: poly(e) for e in json.load(open('data/osm.json', encoding='utf-8'))['elements']}
caldas = poly(json.load(open('data/osm_caldas.json', encoding='utf-8'))['elements'][0])
munis['Manizales'] = caldas.difference(unary_union(list(munis.values())))
# limpia astillas que deja la resta
munis['Manizales'] = max(getattr(munis['Manizales'], 'geoms', [munis['Manizales']]), key=lambda p: p.area)
assert len(munis) == 27, sorted(munis)
names = sorted(munis)
simp = shapely.coverage_simplify([munis[n] for n in names], tolerance=0.0006)  # ~65 m, sin huecos entre vecinos
def rnd(c): return [round(c[0], 4), round(c[1], 4)] if isinstance(c[0], float) else [rnd(x) for x in c]
feats = [{'type': 'Feature', 'properties': {'m': n}, 'geometry': {'type': mapping(g)['type'], 'coordinates': rnd(json.loads(json.dumps(mapping(g)['coordinates'])))}} for n, g in zip(names, simp)]
json.dump({'type': 'FeatureCollection', 'features': feats}, open('docs/caldas.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(len(feats), 'municipios', round(sum(g.area for g in simp) / caldas.area, 4), 'cobertura')
