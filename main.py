# NOTE:
# Revit external command data object.  Retrieves an object that represents the View external command work on.
# Set variable through the IExternalCommand interface / Leave as None through Dynamo.
revit = None  # type: ExternalCommandData # type: ignore

# NOTE:
# Absolute path to the directory containing main.py.
# Set variable through the IExternalCommand interface / Replace manually through Dynamo.
project_dir: str = None  # type: str

import sys
sys.path.append(project_dir)

# Only while debugging, reload user modules
if 'modules' in sys.modules: del sys.modules['modules'] 
import modules # modules.py

import sys
import random

from Autodesk.Revit.DB import (
    Transaction,
    FilteredElementCollector, ElementId, BuiltInCategory, BuiltInParameter,
    ParameterElement,
    Wall,
    ReferenceIntersector, ElementClassFilter, FindReferenceTarget
)
from Autodesk.Revit.UI import TaskDialog, ExternalCommandData

from internal.context import Context # Revit Model context

context = Context(revit)
doc = context.doc

from model import InsolationScale

res = dict()


view3D = doc.GetElement(ElementId(326767))
wall_filter = ElementClassFilter(Wall)
intersector = ReferenceIntersector(
    wall_filter,
    FindReferenceTarget.Element,
    view3D
)
materials = {
    'shadow': ElementId(351245),
    'sun': ElementId(323956),
    'suppressed': ElementId(351905),
}

intersector = ReferenceIntersector(view3D)


transaction = Transaction(doc)
transaction.Start('Build InsolcationScale(s)')

generics = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Mass).WhereElementIsNotElementType().ToElementIds() 
for i in generics: doc.Delete(i)


windows = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).WhereElementIsNotElementType().ToElements()

for window in windows:
    scale = InsolationScale(doc, materials)
    scale.place(window, intersector)
    total, range = scale.range

    window.LookupParameter('InsolationRange').Set(range)
    window.LookupParameter('Insolation').Set(round(total, 2) * 3600)

    shape, message = scale.show()
    if shape:
        shape.LookupParameter('InsolationRange').Set(range)
        shape.LookupParameter('Insolation').Set(round(total, 2) * 3600)

transaction.Commit()

OUT = res
