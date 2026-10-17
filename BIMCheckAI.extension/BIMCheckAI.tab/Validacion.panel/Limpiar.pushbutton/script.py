# -*- coding: utf-8 -*-
"""
BIMCheck AI - Restaurar Vista
Elimina las sobrescrituras gráficas y devuelve los colores originales en la vista activa.
"""

from pyrevit import revit, DB
from Autodesk.Revit.UI import TaskDialog

doc = revit.doc
vista = doc.ActiveView

if not vista or vista.IsTemplate:
    TaskDialog.Show("BIMCheck AI", "La vista activa no es válida o es una plantilla de vista.")
else:
    # 1. Coleccionar los elementos en la vista activa
    elementos_en_vista = (
        DB.FilteredElementCollector(doc, vista.Id)
        .WhereElementIsNotElementType()
    )

    # 2. Configuración gráfica limpia (por defecto)
    config_limpia = DB.OverrideGraphicSettings()

    # 3. Transacción para restablecer la vista
    transaccion = DB.Transaction(doc, "BIMCheck AI - Limpiar Colores")
    transaccion.Start()

    try:
        for elemento in elementos_en_vista:
            vista.SetElementOverrides(elemento.Id, config_limpia)

        transaccion.Commit()

        # Deseleccionar elementos si quedaron marcados
        from System.Collections.Generic import List
        revit.uidoc.Selection.SetElementIds(List[DB.ElementId]())

        TaskDialog.Show(
            "BIMCheck AI",
            "Vista restaurada con éxito.\nSe eliminaron las marcas de color del modelo."
        )

    except Exception as e:
        transaccion.RollBack()
        TaskDialog.Show(
            "BIMCheck AI",
            "Error al limpiar la vista:\n{}".format(e)
        )