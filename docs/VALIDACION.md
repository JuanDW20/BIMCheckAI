# Validación

## Revisión de esta entrega

Se revisó la sintaxis Python sin ejecutar comandos en Revit y se verificaron los enlaces relativos de Markdown. El código funcional se conserva idéntico a los dos archivos de origen. Esta revisión no ejecuta Gemini ni demuestra compatibilidad de una versión de Revit.

## Prueba manual pendiente

Ejecuta en una copia de un modelo y registra versiones, unidades, idioma, fecha, resultados esperados y obtenidos.

| Caso | Resultado esperado |
| --- | --- |
| Puerta sin Marca | sin_marca crítico |
| Puerta y ventana con igual Marca | marca_duplicada para ambas |
| Dos muros con igual Marca | duplicados dentro de Muros según implementación actual |
| Elemento aplicable sin nivel | nivel_obligatorio crítico |
| Barandilla sin nivel | Sin hallazgo de nivel |
| Puertas de 1.89, 1.90, 2.40 y 2.41 m | Advertencia solo en 1.89 y 2.41, sujeto al formato actual |
| Tipo de muro sin AQ-WALL- | Advertencia de nomenclatura |
| Sin clave Gemini | Reporte con agrupación local |
| Sin hallazgos | Resumen local sin consulta a Gemini |
| Sin acceso a Chart.js | Reporte textual e IDs utilizables |
| ID pulsado en HTML | Panel detallado y filas resaltadas |
| Limpiar con overrides previos | Documentar pérdida actual de overrides por elemento |

Compara siempre `hallazgos.json` con el reporte. Anonimiza datos antes de adjuntar evidencias en GitHub.
