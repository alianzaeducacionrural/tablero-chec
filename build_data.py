"""Lee los Excel de data/ y del proyecto y genera docs/data.json (agregado, sin datos personales)
y apps-script/Datos.js (mismos datos, para crear las bases en Drive).
Entradas: data/actividades.xlsx (Informe U Campo), data/estudiantes.xlsx (Activos Técnicos),
'CHEC Convenios y metas.xlsx' (metas 2026) y docs/caldas.json (nombres oficiales de municipios)."""
import json, re, unicodedata
import pandas as pd


def key(s):
    return ''.join(c for c in unicodedata.normalize('NFD', ' '.join(str(s).lower().split())) if unicodedata.category(c) != 'Mn')


def clean(s):
    return ' '.join(str(s).split())


MUNI = {key(f['properties']['m']): f['properties']['m'] for f in json.load(open('docs/caldas.json', encoding='utf-8'))['features']}
MUNI[key('Belálcazar')] = 'Belalcázar'


def mname(s):
    k = key(s)
    assert k in MUNI, f'municipio sin mapa: {s}'
    return MUNI[k]


zonas = pd.read_excel('data/estudiantes.xlsx', sheet_name='BA')
ZONA = {mname(m): z for m, z in zip(zonas.Municipio, zonas.Zona)}
assert len(ZONA) == 27

# --- Estructura del programa (Línea > Componente), igual al informe de financiación de CHEC
U_CAMPO = ('Educación Superior', 'La Universidad en el Campo')
LINEA = {
    'Educación Media': ('Educación para el Trabajo', 'Educación Media'),
    'Capacitación': ('Educación para el Trabajo', 'Educación Media'),
    'Emprendimiento': ('Educación para el Trabajo', 'Emprendimiento'),
    'Empresarismo': ('Educación Superior', 'Empresarismo'),
    'Inserción Laboral': ('Conexión Laboral', 'Inserción Laboral'),
    'Microempresarios Rurales': ('Conexión Laboral', 'Microempresarios Rurales'),
    'Microempresarios': ('Conexión Laboral', 'Microempresarios Rurales'),
}
for p in ['Acompañamiento', 'Desarrollo del plan curricular', 'Dotación', 'Estrategia de permanencia',
          'Estrategias de permanencia', 'Focalización', 'Pruebas Saber T y T']:
    LINEA[p] = U_CAMPO

# --- Instituciones educativas: unifica variantes de escritura; lo que no es un colegio queda vacío
NO_IE = re.compile(r'^(egresados|empresarios|microempresarios|empresas|u de |u catolica|ies cinoc|grupo)|\s-\s')
IE_FIX = {'naranajal': 'naranjal', 'maleteria': 'malteria', 'santagueda': 'santagueda', 'gomez fernandez': 'gomez fernandez',
          'gregorio gutierrez': 'gregorio gutierrez gonzalez', 'luis felipe gutierrez': 'luis felipe gutierrez loaiza',
          'fortunato gaviria': 'fortunato gaviria botero', 'eduardo gomes arrubla': 'eduardo gomez arrubla',
          'san antonio de padua serafico': 'serafico san antonio de padua', 'alegrias': 'alegrias', 'francisco jose caldas': 'francisco jose de caldas'}
IE_NOMBRE = {}


def ie(s):
    if pd.isna(s):
        return ''
    s = re.sub(r'^Instituci[oó]n Educativa\s+', '', clean(s))
    k = key(s)
    if NO_IE.search(k):
        return ''
    k = IE_FIX.get(k, k)
    IE_NOMBRE.setdefault(k, {}).setdefault(s, 0)
    IE_NOMBRE[k][s] += 1
    return k


# --- Inversión (Base Datos)
d = pd.read_excel('data/actividades.xlsx', sheet_name='Base Datos').iloc[:, :11]
d.columns = [c.strip() for c in d.columns]
d['Proceso'] = d.Proceso.map(clean)
assert set(d.Proceso) <= set(LINEA), set(d.Proceso) - set(LINEA)
d['grupo'] = d.Convenio.map(lambda c: 'CHEC' if c == 'CHEC' else 'Otros aliados')
d['tipo'] = d['Estado Convenio'].map(lambda e: 'Adicional al convenio' if e == 'Adicional al convenio' else 'Convenio')  # reinversión = convenio
d['m'] = d.Municipio.map(mname)
d['zona'] = d.m.map(ZONA)
d['linea'] = d.Proceso.map(lambda p: LINEA[p][0])
d['comp'] = d.Proceso.map(lambda p: LINEA[p][1])
d['nivel'] = [('Tecnológico' if re.search(r'tecn[oó]l', key(a)) else 'Técnico profesional') if c == U_CAMPO[1] else ''
              for a, c in zip(d.Actividad, d.comp)]
d['act'] = d.Actividad.map(clean)
d['ie'] = d.Institucion.map(ie)
inv = (d.groupby(['Año', 'grupo', 'tipo', 'm', 'zona', 'linea', 'comp', 'nivel', 'act', 'ie'], as_index=False)
         .agg(valor=('Valor', 'sum'), cant=('Cantidad', 'sum')))
inv['valor'] = inv.valor.round(2)  # con decimales para que los totales cuadren al peso
inv['cant'] = inv.cant.fillna(0).round(0).astype('int64')

# --- Estudiantes técnicos desde 2024 (año = cohorte de ingreso)
s = pd.read_excel('data/estudiantes.xlsx', sheet_name=0)
s.columns = [str(c).strip() for c in s.columns]
s = s[s['Año'] >= 2024].copy()
s['fin'] = s.Financiador.fillna('Sin financiador').map(clean).replace({'COLLECTIVE': 'Collective'})
s['grupo'] = s.fin.map(lambda f: 'CHEC' if f == 'CHEC' else 'Otros aliados')
s['m'] = s.Municipio.map(mname)
s['zona'] = s.m.map(ZONA)
s['e'] = s.Estado.map(clean)
s['u'] = s.Universidad.map(clean)
s['gen'] = s['Género'].fillna('Sin dato')


def programa(p):
    p = clean(p)
    micro = p.startswith('Microcredenciales')
    p = re.sub(r'^Microcredenciales \((.*)\)$', r'\1', p)
    p = re.sub(r'^(T\.P\.|Técnico Profesional) en ', '', p).replace(' (modalidad combinada)', '')
    for a, b in [('Cofiguración', 'Configuración'), ('Matenimiento', 'Mantenimiento'), ('Turisticas', 'Turísticas'), ('Informaticos', 'Informáticos')]:
        p = p.replace(a, b)
    return p + (' (microcredencial)' if micro else '')


s['prog'] = s.Programa.map(programa)
s['ie'] = s['Institución Educativa'].map(ie)
est = (s.groupby(['Año', 'grupo', 'm', 'zona', 'e', 'u', 'prog', 'gen', 'ie'], as_index=False).size()
         .rename(columns={'size': 'n'}))

# nombre visible de cada institución: la escritura más usada
IE = {k: max(v, key=v.get) for k, v in IE_NOMBRE.items()}
IE['eduardo gomez arrubla'] = 'Eduardo Gómez Arrubla'
inv['ie'] = inv.ie.map(lambda k: IE.get(k, ''))
est['ie'] = est.ie.map(lambda k: IE.get(k, ''))

# --- Metas y ejecución del convenio CHEC 2026
mt = pd.read_excel('CHEC Convenios y metas.xlsx', sheet_name='U Campo 2026', header=None).iloc[2:40]
PROY = {'Educación Media': ('Educación para el Trabajo', 'Educación Media', ''),
        'Emprendimiento': ('Educación para el Trabajo', 'Emprendimiento', ''),
        'Técnico Profesional': U_CAMPO + ('Técnico profesional',),
        'Tecnólogo Profesional': U_CAMPO + ('Tecnológico',),
        'Empresarismo': ('Educación Superior', 'Empresarismo', ''),
        'Inserción Laboral': ('Conexión Laboral', 'Inserción Laboral', ''),
        'Microempresarios': ('Conexión Laboral', 'Microempresarios Rurales', '')}
metas = []
for r in mt.itertuples(index=False):
    linea, comp, nivel = PROY[clean(r[0])]
    metas.append({'linea': linea, 'comp': comp, 'nivel': nivel, 'proc': '' if pd.isna(r[1]) else clean(r[1]), 'act': clean(r[2]),
                  'meta': int(r[3]), 'valor': round(float(r[5])), 'chec': round(float(r[6] or 0)) if not pd.isna(r[6]) else 0,
                  'comite': 0 if pd.isna(r[7]) else round(float(r[7])), 'estado': clean(r[8]),
                  'ejec': int(r[17] or 0), 'vejec': round(float(r[18] or 0))})
assert abs(sum(m['valor'] for m in metas) - 950_000_000) < 5, sum(m['valor'] for m in metas)

out = {'inv': inv.rename(columns={'Año': 'a'}).to_dict('records'),
       'est': est.rename(columns={'Año': 'a'}).to_dict('records'),
       'metas': metas}
json.dump(out, open('docs/data.json', 'w', encoding='utf-8'), separators=(',', ':'), ensure_ascii=False)
open('apps-script/Datos.js', 'w', encoding='utf-8').write('const DATA = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n')

# autocomprobación contra el informe de financiación CHEC 2026
c26 = inv[(inv.grupo == 'CHEC') & (inv['Año'] == 2026)].groupby('comp').valor.sum()
for comp, v in {'Educación Media': 81_673_175, 'Emprendimiento': 30_376_700, 'Empresarismo': 56_183_438,
                'Inserción Laboral': 175_563_200, 'La Universidad en el Campo': 575_749_119}.items():
    assert abs(c26[comp] - v) < 5, (comp, c26[comp], v)
print(len(inv), 'filas inv |', len(est), 'filas est |', len(metas), 'metas |', len(IE), 'instituciones')
print(c26.to_string())
