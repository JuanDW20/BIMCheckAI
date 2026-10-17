# Estado y seguimiento

Corte documental: 17 de octubre de 2026.

| Área | Evidencia | Estado |
| --- | --- | --- |
| Extracción, reglas, IA y HTML | Código de Exportar revisado | Implementado; pendiente repetir prueba en Revit |
| Restablecer vista | Código de Limpiar revisado | Implementado; revisar alcance de sobrescrituras |
| Dos modelos reales | Declaración del documento de entrega | Reportado por el autor; sin repetición en esta revisión |
| Manual, arquitectura y reglas | Archivos de este repositorio | Documentado |
| Informe, video y presentación final | Documento fuente, fecha objetivo 19 de octubre sin año explícito | Pendiente de confirmar entrega |
| Publicación en GitHub | Repositorio privado JuanDW20/BIMCheckAI | Publicado con código y documentación inicial |

## Backlog propuesto

Las casillas reflejan trabajo pendiente, sin asignaciones ni fechas inventadas. Crea una issue por mejora y enlaza el pull request que la resuelva.

- [ ] P1 — Convertir alturas desde unidades internas de Revit y recuperar parámetros del tipo cuando corresponda. Aceptación: puertas equivalentes en m y mm producen el mismo resultado.
- [ ] P1 — Calcular KPI desde hallazgos determinísticos y validar/reconciliar el JSON de Gemini. Aceptación: una respuesta con cantidades o IDs alterados no cambia los totales reales.
- [ ] P1 — Limitar Limpiar a sobrescrituras propias o preservar/restaurar el estado anterior. Aceptación: personalizaciones ajenas permanecen intactas.
- [ ] P1 — Registrar matriz de Revit, pyRevit y motor Python realmente probados con evidencias de dos modelos anonimizadas.
- [ ] P2 — Sustituir nombres localizados por identificadores estables. Aceptación: modelo equivalente en español e inglés conserva hallazgos.
- [ ] P2 — Ajustar nomenclatura para comprobar inicio y acordar alcance de duplicados por categoría.
- [ ] P2 — Guardar resultados por modelo y fecha, con identificador de ejecución y versión del catálogo.
- [ ] P2 — Separar el motor de reglas del comando Revit y añadir pruebas unitarias de límites y exclusiones.
- [ ] P2 — Registrar errores de API sin claves ni datos sensibles y mejorar la espera durante solicitudes.
- [ ] P3 — Fijar versión o distribuir Chart.js para mejorar reproducibilidad del reporte.
- [ ] P3 — Completar informe técnico, video y presentación; confirmar la fecha final.
- [ ] P3 — Definir licencia y política de publicación de ejemplos del modelo.

P1 indica corrección o fiabilidad prioritaria; P2 robustez y mantenibilidad; P3 entrega y distribución. Son prioridades propuestas durante la revisión, no compromisos del equipo.


