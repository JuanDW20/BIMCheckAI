#! python3
# -*- coding: utf-8 -*-
"""
BIMCheck AI - Pipeline Integral Autónomo
Extracción (Fase 2) -> Reglas (Fase 3) -> IA Gemini (Fase 4) -> Dashboard HTML (Fase 5)
"""

from pyrevit import revit, DB
from Autodesk.Revit.UI import TaskDialog
import html
import json
import os
import time
import socket
import webbrowser
import urllib.request
import urllib.error

# =======================================================================
# CONFIGURACIÓN Y CONSTANTES
# =======================================================================
doc = revit.doc

CARPETA_BASE = os.path.join(os.path.expanduser("~"), "BIMCheckAI")
CARPETA_EXPORTS = os.path.join(CARPETA_BASE, "exports")
CARPETA_REPORTS = os.path.join(CARPETA_BASE, "reports")
os.makedirs(CARPETA_EXPORTS, exist_ok=True)
os.makedirs(CARPETA_REPORTS, exist_ok=True)

MODELOS_GEMINI = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"

CATEGORIAS_WHITELIST = {
    int(DB.BuiltInCategory.OST_Walls): "Muros",
    int(DB.BuiltInCategory.OST_Doors): "Puertas",
    int(DB.BuiltInCategory.OST_Windows): "Ventanas",
    int(DB.BuiltInCategory.OST_Floors): "Suelos",
    int(DB.BuiltInCategory.OST_Roofs): "Cubiertas",
    int(DB.BuiltInCategory.OST_Ceilings): "Techos",
    int(DB.BuiltInCategory.OST_Columns): "Pilares arquitectónicos",
    int(DB.BuiltInCategory.OST_StructuralColumns): "Pilares estructurales",
    int(DB.BuiltInCategory.OST_StructuralFraming): "Vigas y armazón",
    int(DB.BuiltInCategory.OST_StructuralFoundation): "Cimentación",
    int(DB.BuiltInCategory.OST_Stairs): "Escaleras",
    int(DB.BuiltInCategory.OST_StairsRailing): "Barandillas",
    int(DB.BuiltInCategory.OST_CurtainWallPanels): "Paneles de muro cortina",
    int(DB.BuiltInCategory.OST_CurtainWallMullions): "Montantes de muro cortina",
    int(DB.BuiltInCategory.OST_Ramps): "Rampas",
    int(DB.BuiltInCategory.OST_GenericModel): "Modelos genéricos",
}

# Categorias cuyo parametro de Nivel normalmente esta vacio porque heredan
# la posicion de su elemento anfitrion (ej. una barandilla de una escalera,
# un panel de un muro cortina). Se excluyen de la regla "nivel_obligatorio"
# para no generar falsos positivos.
CATEGORIAS_SIN_NIVEL_PROPIO = {
    "Barandillas",
    "Paneles de muro cortina",
    "Montantes de muro cortina",
}

# Categorias que deben seguir la convencion de nombres de tipo del proyecto.
PREFIJOS_NOMENCLATURA = {
    "Muros": "AQ-WALL-",
}


def obtener_numero_id(element_id):
    if hasattr(element_id, "Value"):
        return element_id.Value
    return element_id.IntegerValue


# =======================================================================
# ETAPA 1: EXTRACCIÓN FILTRADA (FASE 2)
# =======================================================================
coleccion = (
    DB.FilteredElementCollector(doc)
    .WhereElementIsNotElementType()
    .WhereElementIsViewIndependent()
)

elementos_extraidos = []

for elemento in coleccion:
    if elemento.Category is None:
        continue

    cat_id = int(obtener_numero_id(elemento.Category.Id))
    if cat_id not in CATEGORIAS_WHITELIST:
        continue

    ficha = {
        "id": str(obtener_numero_id(elemento.Id)),
        "categoria": elemento.Category.Name,
        "parametros": {}
    }

    for parametro in elemento.Parameters:
        nombre = parametro.Definition.Name
        try:
            valor = parametro.AsValueString()
            if valor is None:
                valor = parametro.AsString()
        except Exception:
            valor = None

        ficha["parametros"][nombre] = valor

    elementos_extraidos.append(ficha)

ruta_export = os.path.join(CARPETA_EXPORTS, "export_revit.json")
with open(ruta_export, "w", encoding="utf-8") as f:
    json.dump(elementos_extraidos, f, indent=2, ensure_ascii=False)


# =======================================================================
# ETAPA 2: MOTOR DE REGLAS DETERMINÍSTICO (FASE 3)
# =======================================================================
def _grupo_marca(categoria):
    """Puertas y Ventanas comparten una sola numeracion de Marca en este
    proyecto (se ve en los datos reales: 100, 101, 105, 106... intercaladas
    entre ambas categorias), asi que se tratan como un solo grupo al buscar
    duplicados. El resto de categorias se evalua cada una por su cuenta."""
    if categoria in ("Puertas", "Ventanas"):
        return "Puertas/Ventanas"
    return categoria


def ejecutar_motor_reglas(elementos):
    hallazgos = []
    marcas_vistas = {}

    # Mapeo previo para marcas duplicadas
    for el in elementos:
        marca = el["parametros"].get("Marca")
        if marca and str(marca).strip():
            clave = (_grupo_marca(el["categoria"]), str(marca).strip())
            marcas_vistas.setdefault(clave, []).append(el["id"])

    # Evaluación elemento por elemento
    for el in elementos:
        el_id = el["id"]
        cat = el["categoria"]
        params = el["parametros"]

        # Regla: elementos sin nivel asignado (no aplica a categorias que
        # heredan su posicion de un elemento anfitrion, ver mas arriba).
        if cat not in CATEGORIAS_SIN_NIVEL_PROPIO:
            nivel = (
                params.get("Nivel")
                or params.get("Nivel base")
                or params.get("Restricción de base")
                or params.get("Nivel de referencia")
            )
            if not nivel or not str(nivel).strip():
                hallazgos.append({
                    "elemento_id": el_id,
                    "categoria": cat,
                    "regla": "nivel_obligatorio",
                    "severidad": "critico",
                    "mensaje": f"{cat} sin parámetro de nivel asignado."
                })

        # Regla: Puertas/Ventanas sin Marca asignada
        if cat in ("Puertas", "Ventanas"):
            marca = params.get("Marca")
            if not marca or not str(marca).strip():
                hallazgos.append({
                    "elemento_id": el_id,
                    "categoria": cat,
                    "regla": "sin_marca",
                    "severidad": "critico",
                    "mensaje": f"{cat} sin parámetro 'Marca' asignado."
                })

        # Regla: Altura de puertas fuera de rango estándar (1.90m a 2.40m)
        if cat == "Puertas":
            altura_str = params.get("Altura de extremo inicial") or params.get("Altura desconectada") or params.get("Altura")
            if altura_str:
                try:
                    altura_val = float(str(altura_str).replace(",", ".").split()[0])
                    if altura_val < 1.90 or altura_val > 2.40:
                        hallazgos.append({
                            "elemento_id": el_id,
                            "categoria": cat,
                            "regla": "altura_puerta_estandar",
                            "severidad": "advertencia",
                            "mensaje": f"Puerta con altura de {altura_val}m fuera del rango estándar (1.90m - 2.40m)."
                        })
                except ValueError:
                    pass

        # Regla: nomenclatura de tipo (ej. muros deben empezar con "AQ-WALL-")
        prefijo = PREFIJOS_NOMENCLATURA.get(cat)
        if prefijo:
            tipo = params.get("Tipo") or ""
            if prefijo not in tipo:
                hallazgos.append({
                    "elemento_id": el_id,
                    "categoria": cat,
                    "regla": "nomenclatura_tipo",
                    "severidad": "advertencia",
                    "mensaje": f"El tipo de {cat.lower()} no sigue la convención de nombres '{prefijo}...'."
                })

    # Regla: marcas duplicadas registradas
    for (grupo, marca), ids in marcas_vistas.items():
        if len(ids) > 1:
            for el_id in ids:
                hallazgos.append({
                    "elemento_id": el_id,
                    "categoria": grupo,
                    "regla": "marca_duplicada",
                    "severidad": "critico",
                    "mensaje": f"Marca '{marca}' duplicada en {grupo} ({len(ids)} elementos)."
                })

    return hallazgos

hallazgos_detectados = ejecutar_motor_reglas(elementos_extraidos)

ruta_hallazgos = os.path.join(CARPETA_EXPORTS, "hallazgos.json")
with open(ruta_hallazgos, "w", encoding="utf-8") as f:
    json.dump(hallazgos_detectados, f, indent=2, ensure_ascii=False)


# =======================================================================
# ETAPA 3: CAPA DE IA CON GEMINI (FASE 4)
# =======================================================================
def construir_prompt(hallazgos):
    instrucciones = """
Eres un asistente que interpreta hallazgos de control de calidad de modelos BIM (Revit).
Ya se determino objetivamente que elementos NO cumplen ciertas reglas; tu tarea es SOLO interpretar, agrupar y explicar estos hallazgos.

Devuelve UNICAMENTE un objeto JSON valido, sin texto antes ni despues, sin usar backticks de markdown:
{
  "resumen_ejecutivo": "2-3 frases resumiendo el estado general del modelo",
  "hallazgos_agrupados": [
    {
      "tema": "nombre corto del grupo",
      "cantidad": 0,
      "prioridad": "alta | media | baja",
      "explicacion": "por que importa este problema en lenguaje simple",
      "elementos_afectados": ["id1", "id2"]
    }
  ]
}
Prioridad: 'alta' para critico, 'media' para advertencia, 'baja' para sugerencia. Responde en español.
""".strip()
    return f"{instrucciones}\n\nHallazgos:\n{json.dumps(hallazgos, ensure_ascii=False)}"


_SEVERIDAD_A_PRIORIDAD = {"critico": "alta", "advertencia": "media", "sugerencia": "baja"}
_NOMBRE_REGLA = {
    "nivel_obligatorio": "Elementos sin nivel asignado",
    "sin_marca": "Elementos sin Marca asignada",
    "altura_puerta_estandar": "Puertas con altura fuera de rango",
    "nomenclatura_tipo": "Tipos que no siguen la convención de nombres",
    "marca_duplicada": "Marca duplicada entre elementos",
}


def agrupar_hallazgos_sin_ia(hallazgos):
    """Agrupa los hallazgos por regla, conservando su severidad real
    (convertida a prioridad alta/media/baja). Se usa cuando la IA no esta
    disponible, para que el dashboard no pierda la distincion de severidad
    ni junte todo bajo una sola prioridad "alta" ficticia."""
    grupos = {}
    for h in hallazgos:
        regla = h.get("regla", "desconocida")
        grupos.setdefault(regla, []).append(h)

    resultado = []
    for regla, items in grupos.items():
        severidad = items[0].get("severidad", "advertencia")
        resultado.append({
            "tema": _NOMBRE_REGLA.get(regla, regla),
            "cantidad": len(items),
            "prioridad": _SEVERIDAD_A_PRIORIDAD.get(severidad, "media"),
            "explicacion": items[0].get("mensaje", ""),
            "elementos_afectados": [it["elemento_id"] for it in items],
        })
    return resultado


def consultar_gemini(hallazgos):
    if not hallazgos:
        return {
            "resumen_ejecutivo": "No se encontraron hallazgos: el modelo cumple todas las reglas revisadas.",
            "hallazgos_agrupados": []
        }

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "resumen_ejecutivo": "Auditoría realizada sin IA conectada (no se encontró GEMINI_API_KEY). Se presentan los hallazgos agrupados directamente por el motor de reglas.",
            "hallazgos_agrupados": agrupar_hallazgos_sin_ia(hallazgos)
        }

    payload = json.dumps({
        "contents": [{"parts": [{"text": construir_prompt(hallazgos)}]}],
        "generationConfig": {"thinkingConfig": {"thinkingBudget": 0}}
    }).encode("utf-8")

    for modelo in MODELOS_GEMINI:
        for intento in range(1, 4):
            req = urllib.request.Request(
                URL_GEMINI.format(modelo),
                data=payload,
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.load(resp)
                    texto = data["candidates"][0]["content"]["parts"][0]["text"]
                    texto_limpio = texto.replace("```json", "").replace("```", "").strip()
                    return json.loads(texto_limpio)
            except Exception:
                time.sleep(2)
                continue

    # No se logro contactar a ningun modelo: fallback que SI conserva severidades reales
    return {
        "resumen_ejecutivo": "No fue posible contactar a la IA (revisa tu conexión o el estado del servicio). Se muestran los hallazgos agrupados directamente por el motor de reglas.",
        "hallazgos_agrupados": agrupar_hallazgos_sin_ia(hallazgos)
    }

interpretacion_ia = consultar_gemini(hallazgos_detectados)

ruta_interpretacion = os.path.join(CARPETA_EXPORTS, "interpretacion.json")
with open(ruta_interpretacion, "w", encoding="utf-8") as f:
    json.dump(interpretacion_ia, f, indent=2, ensure_ascii=False)


# =======================================================================
# ETAPA 4: DASHBOARD VISUAL Y APERTURA (FASE 5)
# =======================================================================
resumen = interpretacion_ia.get("resumen_ejecutivo", "")
grupos = interpretacion_ia.get("hallazgos_agrupados", [])

total_h = sum(g.get("cantidad", 0) for g in grupos)
altas = sum(g.get("cantidad", 0) for g in grupos if g.get("prioridad", "").lower() == "alta")
medias = sum(g.get("cantidad", 0) for g in grupos if g.get("prioridad", "").lower() == "media")
bajas = sum(g.get("cantidad", 0) for g in grupos if g.get("prioridad", "").lower() == "baja")

afectados = set()
for g in grupos:
    for el in g.get("elementos_afectados", []):
        afectados.add(str(el))

# Mapeo id -> categoria, para mostrar "1827180 (puertas)" junto a cada ID
# y para que el panel de detalle sepa que categoria tiene el elemento clickeado.
id_a_categoria = {str(el.get("id")): el.get("categoria", "") for el in elementos_extraidos}


def _fila_detalle(h):
    sev = h.get("severidad", "")
    badge_clase = {"critico": "badge-alta", "advertencia": "badge-media", "sugerencia": "badge-baja"}.get(sev, "badge-media")
    el_id = str(h.get("elemento_id", ""))
    # data-id permite que el JS resalte esta fila cuando se hace clic
    # en el chip correspondiente dentro de "Detalle de Hallazgos Agrupados".
    return (
        f"<tr data-id='{html.escape(el_id)}'>"
        f"<td><span class='badge {badge_clase}'>{html.escape(sev)}</span></td>"
        f"<td>{html.escape(el_id)}</td>"
        f"<td>{html.escape(str(h.get('categoria','')))}</td>"
        f"<td><code>{html.escape(str(h.get('regla','')))}</code></td>"
        f"<td>{html.escape(str(h.get('mensaje','')))}</td>"
        "</tr>"
    )

if hallazgos_detectados:
    filas_detalle = "".join(_fila_detalle(h) for h in sorted(
        hallazgos_detectados, key=lambda h: (h.get("severidad") != "critico", h.get("regla", ""))
    ))
    tabla_detalle_html = (
        "<div class='card' style='overflow-x:auto;'>"
        "<table id='tablaCruda' style='width:100%; border-collapse:collapse; font-size:0.85rem;'>"
        "<thead><tr style='text-align:left; background:#f1f5f9;'>"
        "<th style='padding:8px;'>Severidad</th><th style='padding:8px;'>ID elemento</th>"
        "<th style='padding:8px;'>Categoría</th><th style='padding:8px;'>Regla</th>"
        "<th style='padding:8px;'>Detalle</th></tr></thead>"
        f"<tbody>{filas_detalle}</tbody></table></div>"
    )
else:
    tabla_detalle_html = "<div class='card' style='text-align:center; color:var(--success); font-weight:600;'>✔ Sin hallazgos técnicos.</div>"


html_template = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>BIMCheck AI — Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg: #f8fafc; --card: #ffffff; --text: #0f172a; --muted: #64748b;
            --primary: #2563eb; --danger: #ef4444; --warning: #f59e0b; --success: #10b981; --border: #e2e8f0;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 25px; }
        .container { max-width: 1100px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border); padding-bottom: 12px; margin-bottom: 20px; }
        h1 { margin: 0; font-size: 1.6rem; }
        .tag { background: #dbeafe; color: var(--primary); padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.8rem; }
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }
        .kpi-card { background: var(--card); padding: 14px; border-radius: 8px; border: 1px solid var(--border); }
        .kpi-title { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; font-weight: 600; }
        .kpi-val { font-size: 1.6rem; font-weight: 800; margin-top: 4px; }
        .summary-box { background: #eff6ff; border-left: 4px solid var(--primary); padding: 14px 18px; border-radius: 6px; margin-bottom: 20px; line-height: 1.5; }
        .middle-grid { display: grid; grid-template-columns: 1fr 2fr; gap: 15px; margin-bottom: 20px; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
        .finding-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 10px; }
        .badge { padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.7rem; text-transform: uppercase; }
        .badge-alta { background: #fee2e2; color: var(--danger); }
        .badge-media { background: #fef3c7; color: var(--warning); }
        .badge-baja { background: #dcfce7; color: var(--success); }
        .chip { display: inline-block; background: #f1f5f9; color: #334155; padding: 2px 7px; border-radius: 4px; font-family: monospace; font-size: 0.8rem; margin: 2px; border: 1px solid #cbd5e1; }
        button.chip { cursor: pointer; font: inherit; }
        button.chip:hover { background: #e2e8f0; border-color: var(--primary); }
        button.chip:focus-visible { outline: 2px solid var(--primary); outline-offset: 1px; }
        section.detalle { margin-top: 24px; }
        section.detalle h3 { margin-bottom: 10px; }
        section.detalle summary { cursor: pointer; font-weight: 600; margin-bottom: 10px; }
        table code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; }
        #tablaCruda tbody tr.fila-resaltada { background: #fef3c7; }
        #panelDetalle { min-height: 90px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>BIMCheck AI — Auditoría de Calidad</h1>
                <p style="margin: 2px 0 0 0; color: var(--muted); font-size: 0.85rem;">Inspección determinística + Síntesis IA</p>
            </div>
            <span class="tag">Fase 5 • Dashboard</span>
        </header>

        <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-title">Elementos Auditados</div><div class="kpi-val">__ELEM_TOTAL__</div></div>
            <div class="kpi-card"><div class="kpi-title">Total Hallazgos</div><div class="kpi-val">__TOTAL_H__</div></div>
            <div class="kpi-card" style="border-left: 4px solid var(--danger);"><div class="kpi-title">Prioridad Alta</div><div class="kpi-val" style="color:var(--danger)">__ALTAS__</div></div>
            <div class="kpi-card" style="border-left: 4px solid var(--warning);"><div class="kpi-title">Prioridad Media</div><div class="kpi-val" style="color:var(--warning)">__MEDIAS__</div></div>
            <div class="kpi-card" style="border-left: 4px solid var(--success);"><div class="kpi-title">Prioridad Baja</div><div class="kpi-val" style="color:var(--success)">__BAJAS__</div></div>
            <div class="kpi-card"><div class="kpi-title">Elementos Afectados</div><div class="kpi-val">__AFECTADOS__</div></div>
        </div>

        <div class="summary-box">
            <strong style="color: var(--primary);">📌 Resumen Ejecutivo:</strong>
            <p style="margin: 4px 0 0 0;">__RESUMEN__</p>
        </div>

        <div class="middle-grid">
            <div class="card" style="text-align: center;">
                <h3 style="margin-top:0; font-size:0.95rem;">Distribución de Severidad</h3>
                <canvas id="chartPrioridad" style="max-height: 160px;"></canvas>
            </div>
            <div class="card" id="panelDetalle">
                <h3 style="margin-top:0; font-size:0.95rem;">Detalle del elemento seleccionado</h3>
                <div id="detalleContenido" style="font-size:0.85rem; color:var(--muted);">
                    Haz clic en un ID dentro de los hallazgos de abajo para ver aquí el detalle completo de ese elemento.
                </div>
            </div>
        </div>

        <h3 style="margin-bottom: 10px;">Detalle de Hallazgos Agrupados (interpretación IA)</h3>
        <div id="contenedor"></div>

        <section class="detalle">
            <details open>
                <summary>Detalle técnico crudo (motor de reglas)</summary>
                __TABLA_DETALLE__
            </details>
        </section>
    </div>

    <script>
        function escapeHtml(s) {
            return String(s).replace(/[&<>"']/g, c => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
            }[c]));
        }

        const datos = __JSON_DATOS__;
        const datosCrudos = __JSON_CRUDOS__;
        const idACategoria = __JSON_ID_CAT__;

        // Si Chart.js no logra cargar (sin internet, red restringida, etc.)
        // esto no debe tumbar el resto del dashboard (lista de hallazgos,
        // buscador). Por eso va en su propio try/catch.
        try {
            new Chart(document.getElementById('chartPrioridad').getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['Alta', 'Media', 'Baja'],
                    datasets: [{
                        data: [__ALTAS__, __MEDIAS__, __BAJAS__],
                        backgroundColor: ['#ef4444', '#f59e0b', '#10b981']
                    }]
                },
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
            });
        } catch (err) {
            document.getElementById('chartPrioridad').replaceWith(
                Object.assign(document.createElement('p'), {
                    style: 'color:var(--muted); font-size:0.85rem;',
                    textContent: 'No se pudo cargar la gráfica (sin conexión a internet).'
                })
            );
        }

        const cont = document.getElementById('contenedor');
        datos.forEach(h => {
            const div = document.createElement('div');
            div.className = 'finding-card';
            const chips = (h.elementos_afectados || []).map(id => {
                const cat = (idACategoria[id] || '').toLowerCase();
                const etiqueta = cat ? `${id} (${cat})` : String(id);
                // data-id (no un id literal en el onclick) evita cualquier
                // problema de escapado; un solo listener mas abajo escucha
                // todos los chips, incluidos los que se agregan aqui.
                return `<button type="button" class="chip" data-id="${escapeHtml(id)}">${escapeHtml(etiqueta)}</button>`;
            }).join('');
            div.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <strong>${escapeHtml(h.tema)} (${escapeHtml(h.cantidad)})</strong>
                    <span class="badge badge-${escapeHtml((h.prioridad||'').toLowerCase())}">${escapeHtml(h.prioridad)}</span>
                </div>
                <p style="margin: 4px 0 8px 0; color:#334155; font-size:0.9rem;">${escapeHtml(h.explicacion)}</p>
                <div><small style="color:var(--muted); font-weight:600;">IDs afectados (clic para ver detalle):</small> ${chips}</div>
            `;
            cont.appendChild(div);
        });

        const BADGE_POR_SEVERIDAD = { critico: 'badge-alta', advertencia: 'badge-media', sugerencia: 'badge-baja' };

        function mostrarDetalleElemento(id) {
            // Resalta en la tabla cruda todas las filas de este elemento.
            document.querySelectorAll('#tablaCruda tbody tr').forEach(tr => {
                tr.classList.toggle('fila-resaltada', tr.dataset.id === id);
            });
            const primeraFila = document.querySelector(`#tablaCruda tbody tr[data-id="${CSS.escape(id)}"]`);
            if (primeraFila) primeraFila.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

            const cat = idACategoria[id] || '';
            const etiqueta = cat ? `${id} (${cat})` : id;
            const deIA = datos.filter(h => (h.elementos_afectados || []).map(String).includes(id));
            const crudos = datosCrudos.filter(h => String(h.elemento_id) === id);

            let salida = `<div style="margin-bottom:8px; color:var(--text);"><strong style="font-size:0.95rem;">${escapeHtml(etiqueta)}</strong></div>`;

            if (deIA.length === 0 && crudos.length === 0) {
                salida += `<p style="color:var(--success); font-weight:600;">✅ Sin observaciones registradas para este elemento.</p>`;
            } else {
                if (deIA.length) {
                    salida += `<p style="margin:8px 0 4px; font-weight:700; color:var(--muted); text-transform:uppercase; font-size:0.7rem;">Interpretación IA</p>`;
                    deIA.forEach(h => {
                        salida += `<div style="margin-bottom:8px;">
                            <span class="badge badge-${escapeHtml((h.prioridad||'').toLowerCase())}">${escapeHtml(h.prioridad)}</span>
                            <strong style="margin-left:4px;">${escapeHtml(h.tema)}</strong>
                            <p style="margin:4px 0 0; color:var(--text);">${escapeHtml(h.explicacion)}</p>
                        </div>`;
                    });
                }
                if (crudos.length) {
                    salida += `<p style="margin:8px 0 4px; font-weight:700; color:var(--muted); text-transform:uppercase; font-size:0.7rem;">Detalle técnico (motor de reglas)</p>`;
                    crudos.forEach(h => {
                        const badgeClase = BADGE_POR_SEVERIDAD[h.severidad] || 'badge-media';
                        salida += `<div style="margin-bottom:6px;">
                            <span class="badge ${badgeClase}">${escapeHtml(h.severidad)}</span>
                            <code style="margin-left:4px;">${escapeHtml(h.regla)}</code>
                            <p style="margin:4px 0 0; color:var(--text);">${escapeHtml(h.mensaje)}</p>
                        </div>`;
                    });
                }
            }

            document.getElementById('detalleContenido').innerHTML = salida;
            document.getElementById('panelDetalle').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        // Un solo listener para todos los chips, incluidos los agregados
        // dinamicamente arriba (delegacion de eventos).
        document.addEventListener('click', (e) => {
            const boton = e.target.closest('.chip[data-id]');
            if (boton) mostrarDetalleElemento(boton.dataset.id);
        });
    </script>
</body>
</html>
"""

# json.dumps puede incluir la secuencia "</script>" si algun texto de la IA
# la contiene, lo que cerraria el <script> antes de tiempo. Se escapa "</"
# como es practica estandar al embeber JSON dentro de un <script>.
def _json_seguro(valor):
    return json.dumps(valor, ensure_ascii=False).replace("</", "<\\/")

json_datos_seguro = _json_seguro(grupos)
json_crudos_seguro = _json_seguro(hallazgos_detectados)
json_id_cat_seguro = _json_seguro(id_a_categoria)

html_final = (
    html_template
    .replace("__ELEM_TOTAL__", str(len(elementos_extraidos)))
    .replace("__TOTAL_H__", str(total_h))
    .replace("__ALTAS__", str(altas))
    .replace("__MEDIAS__", str(medias))
    .replace("__BAJAS__", str(bajas))
    .replace("__AFECTADOS__", str(len(afectados)))
    .replace("__RESUMEN__", html.escape(resumen))
    .replace("__TABLA_DETALLE__", tabla_detalle_html)
    .replace("__JSON_DATOS__", json_datos_seguro)
    .replace("__JSON_CRUDOS__", json_crudos_seguro)
    .replace("__JSON_ID_CAT__", json_id_cat_seguro)
)

ruta_html = os.path.join(CARPETA_REPORTS, "dashboard_bimcheck.html")
with open(ruta_html, "w", encoding="utf-8") as f:
    f.write(html_final)

webbrowser.open(os.path.abspath(ruta_html))

TaskDialog.Show(
    "BIMCheck AI",
    "Auditoría ejecutada con éxito.\n\n"
    "- Elementos auditados: {}\n"
    "- Observaciones detectadas: {}\n\n"
    "El dashboard se abrió automáticamente en tu navegador.".format(
        len(elementos_extraidos), total_h
    )
)
