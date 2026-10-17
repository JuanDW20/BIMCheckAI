# Catálogo de reglas

Las reglas reflejan convenciones de este proyecto; no constituyen una certificación normativa universal.

| Identificador | Severidad | Comportamiento implementado |
| --- | --- | --- |
| `nivel_obligatorio` | critico | Busca Nivel, Nivel base, Restricción de base o Nivel de referencia; genera hallazgo si no obtiene un valor no vacío. Excluye Barandillas, Paneles de muro cortina y Montantes de muro cortina. |
| `sin_marca` | critico | Puertas y Ventanas deben tener Marca no vacía. |
| `marca_duplicada` | critico | Agrupa marcas tras quitar espacios exteriores. Puertas y Ventanas comparten grupo; el resto se revisa por categoría. Genera un hallazgo por cada elemento implicado. |
| `altura_puerta_estandar` | advertencia | En Puertas, consulta Altura de extremo inicial, Altura desconectada o Altura; interpreta el primer número como metros y advierte fuera de 1.90 a 2.40, inclusive los extremos válidos. Un valor no interpretable se omite. |
| `nomenclatura_tipo` | advertencia | En Muros, comprueba que Tipo contenga AQ-WALL-. Actualmente usa pertenencia, no una comprobación estricta de inicio. Tipo vacío genera hallazgo. |

## Diferencias respecto de la entrega parcial

El documento describe principalmente duplicados entre puertas y ventanas; el código también revisa duplicados dentro de otras categorías. Describe una convención de prefijo, mientras el código acepta la cadena en cualquier posición. Describe un HTML autocontenido; los datos están incluidos, pero la gráfica depende de la CDN.

## Configuración actual

Las categorías y prefijos se editan en las constantes del script Exportar. El rango de altura está escrito dentro de `ejecutar_motor_reglas`. Antes de adaptarlos, registra la convención acordada del proyecto y prueba con modelos conocidos.
