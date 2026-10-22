# BIMCheck AI

Asistente de control de calidad para modelos BIM de Autodesk Revit, ejecutado mediante pyRevit. Extrae elementos, aplica reglas determinísticas y genera un reporte HTML con interpretación opcional de Google Gemini.

## Estado

Base documental del 17 de octubre de 2026. Se revisaron los dos scripts de la extensión. El documento de entrega parcial informa validación en dos modelos reales; esa ejecución no se reprodujo durante esta revisión. Las versiones exactas compatibles de Revit y pyRevit están pendientes de registrar.

## Inicio rápido

1. Instala Autodesk Revit y una versión de pyRevit con motor Python 3 compatible con tu instalación.
2. Copia `BIMCheckAI.extension` a una ruta de extensiones reconocida por pyRevit; habitualmente `%APPDATA%/pyRevit/Extensions/`.
3. Recarga pyRevit y verifica la pestaña **BIMCheckAI**, panel **Validacion**.
4. Opcionalmente configura `GEMINI_API_KEY` como variable de entorno del usuario y reinicia Revit para que la reciba. Nunca guardes la clave en el repositorio.
5. Abre un modelo y pulsa **Exportar**. El dashboard se abrirá en el navegador.

Los resultados se escriben en `%USERPROFILE%/BIMCheckAI/exports/` y `%USERPROFILE%/BIMCheckAI/reports/`. Cada ejecución sustituye los archivos anteriores con el mismo nombre. Guarda una copia por revisión para conservar el historial.

## Documentación

- [Instalación y uso](docs/USO.md)
- [Arquitectura y datos](docs/ARQUITECTURA.md)
- [Catálogo de reglas](docs/REGLAS.md)
- [Estado y trabajo pendiente](docs/SEGUIMIENTO.md)
- [Validación manual](docs/VALIDACION.md)
- [Contribuciones y control de versiones](CONTRIBUTING.md)
- [Registro de cambios](CHANGELOG.md)

## Alcance y datos

Exportar inspecciona instancias del documento activo de 16 categorías constructivas; no recorre documentos vinculados. El motor determina los hallazgos y Gemini los interpreta. Sin clave o ante fallos de la API, el reporte utiliza agrupación local. El HTML incluye los datos pero carga Chart.js desde una CDN; sin internet puede faltar la gráfica.

Gemini recibe los hallazgos, incluidos IDs, categorías, reglas y mensajes. Evalúa la autorización para enviar datos del proyecto antes de activar la API. Los JSON y reportes pueden contener información del modelo y se excluyen del control de versiones.

