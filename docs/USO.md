# Instalación y uso

## Requisitos

Windows, Autodesk Revit, pyRevit y un motor Python 3 compatible para el botón Exportar (`#! python3`). No existe un paquete instalable ni un archivo de dependencias pip: el script emplea bibliotecas estándar y APIs proporcionadas por Revit y pyRevit. La compatibilidad exacta debe comprobarse en el equipo destino.

## Flujo de auditoría

Abre el modelo, ejecuta Exportar, espera a que termine y revisa el reporte. La operación extrae parámetros, genera hallazgos, intenta interpretarlos con Gemini y abre el HTML. Los reintentos se ejecutan dentro del comando y pueden tardar varios minutos.

En el reporte consulta el resumen, los grupos y la tabla técnica. Pulsa un ID para ver sus hallazgos y resaltar las filas correspondientes. El ID del HTML no selecciona el elemento dentro de Revit. Un elemento puede tener varios hallazgos: sus cantidades no son equivalentes.

## Archivos generados

| Ruta relativa a `%USERPROFILE%/BIMCheckAI` | Contenido |
| --- | --- |
| `exports/export_revit.json` | Elementos y parámetros extraídos |
| `exports/hallazgos.json` | Hallazgos determinísticos |
| `exports/interpretacion.json` | Interpretación de Gemini o agrupación local |
| `reports/dashboard_bimcheck.html` | Reporte visual |

No se conserva un historial automáticamente. Copia los cuatro archivos a una carpeta por modelo y fecha antes de repetir una auditoría.

## Botón Limpiar

Restablece las sobrescrituras gráficas por elemento de todos los elementos recolectados en la vista activa y vacía la selección. No distingue colores puestos por BIMCheck AI de personalizaciones previas del usuario. Valida la vista antes de usarlo. Rechaza vistas nulas o plantillas y utiliza una transacción con reversión ante errores.

## Incidencias habituales

- Pestaña ausente: comprueba la ruta de extensiones y recarga pyRevit.
- Error de motor: comprueba que Exportar ejecuta Python 3 compatible con Revit.
- Resumen sin IA: comprueba que Revit recibió `GEMINI_API_KEY`; el reporte local sigue disponible.
- Gráfica ausente: comprueba el acceso a la CDN de Chart.js.
- Alturas inesperadas: revisa unidades y formato de parámetros; el código interpreta el número mostrado como metros sin convertir unidades.
- Hallazgos inesperados de nivel o categoría: verifica el idioma de Revit; las reglas buscan nombres en español.
