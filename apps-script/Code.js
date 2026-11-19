const CARPETA_ID = '1WZH72Z-sjE5ha9_xMLBwgCv0SWsXHmP7';
// Una hoja de cálculo por tabla; las columnas salen de los datos que genera build_data.py
const BASES = { inv: 'BD Inversión CHEC', est: 'BD Estudiantes técnicos CHEC', metas: 'BD Metas CHEC 2026' };

// Crea o reemplaza el contenido de las bases en la carpeta de Drive. Ejecutar a mano tras cada actualización.
function crearBases() {
  const carpeta = DriveApp.getFolderById(CARPETA_ID);
  Object.keys(BASES).forEach(k => escribir_(carpeta, BASES[k], DATA[k]));
}

function escribir_(carpeta, nombre, filas) {
  const cols = Object.keys(filas[0]);
  const it = carpeta.getFilesByName(nombre);
  const existe = it.hasNext();
  const ss = existe ? SpreadsheetApp.open(it.next()) : SpreadsheetApp.create(nombre);
  if (!existe) DriveApp.getFileById(ss.getId()).moveTo(carpeta);
  const sh = ss.getSheets()[0];
  sh.clear();
  sh.getRange(1, 1, filas.length + 1, cols.length).setValues([cols].concat(filas.map(f => cols.map(c => f[c]))));
  sh.setFrozenRows(1);
  Logger.log(nombre + ': ' + filas.length + ' filas -> ' + ss.getUrl());
}

// Sirve las bases como JSON para el tablero (GitHub Pages).
function doGet() {
  const carpeta = DriveApp.getFolderById(CARPETA_ID);
  const out = {};
  Object.keys(BASES).forEach(k => {
    const it = carpeta.getFilesByName(BASES[k]);
    if (!it.hasNext()) return;
    const v = SpreadsheetApp.open(it.next()).getSheets()[0].getDataRange().getValues();
    out[k] = v.slice(1).map(r => Object.fromEntries(v[0].map((c, i) => [c, r[i]])));
  });
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}
