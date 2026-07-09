# NOTE:
# Revit external command data object.  Retrieves an object that represents the View external command work on.
# Set variable through the IExternalCommand interface / Leave as None through Dynamo.
revit = None  # type: ExternalCommandData # type: ignore

# NOTE:
# Absolute path to the directory containing main.py.
# Set variable through the IExternalCommand interface / Replace manually through Dynamo.
project_dir: str = None  # type: str

import os
import sys
import json
import random
sys.path.append(project_dir)

# Only while debugging, reload user modules
if 'modules' in sys.modules: del sys.modules['modules'] 
import modules # modules.py


from System.Collections.Generic import List
from Autodesk.Revit.DB import (
    Transaction,
    FilteredElementCollector, ElementId, BuiltInCategory, BuiltInParameter,
    ParameterElement, View3D,
    Wall, Material,
    ReferenceIntersector, ElementClassFilter, FindReferenceTarget
)
from Autodesk.Revit.UI import TaskDialog, ExternalCommandData

from internal.context import Context # Revit Model context

context = Context(revit)
doc = context.doc

from model import InsolationScale
from util import set_lookup


category = BuiltInCategory.OST_Mass
step, day, view_name = IN[0], IN[1], IN[2]  #type: ignore
res = dict()


try: # read data from *.json
    options = os.path.join(project_dir, 'config.json')
    with open(options, 'r') as file:
        config = json.load(file)
except IOError:
    raise "Error: File %s doesn't exist." % options
except json.JSONDecodeError:
    raise 'Error: File %s is not valid JSON.' % options

# Create Metarials palette
materials = FilteredElementCollector(doc).OfClass(Material).ToElements()
names = config.get('Materials')

palette = dict()
for name in names:
    for material in materials:
        if material.Name == names[name]:
            palette[name] = material.Id
            break
    else:
        i = random.randint(0, len(materials) - 1)
        palette[name] = materials[i].Id

# Extract Parameter names
parameters = config.get('Parameters')
InsolationRange = parameters.get('InsolationRange')
Insolation = parameters.get('Insolation')

# Extract IsolationScale Family name
families = config.get('Families')
InsolationRuler = families.get('InsolationRuler')

# Find View3D and create ReferenceIntersector
views = FilteredElementCollector(doc).OfClass(View3D).ToElements()
for view in views:
    if view.IsTemplate: continue
    view3D = view
    if view.Name == view_name: break

intersector = ReferenceIntersector(view3D)


transaction = Transaction(doc)
transaction.Start('Build InsolcationScale(s)')

previous = FilteredElementCollector(doc).OfCategory(category).WhereElementIsNotElementType().ToElementIds() 
doc.Delete(List[ElementId](previous))

windows = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).WhereElementIsNotElementType().ToElements()

scale = InsolationScale(doc, materials)
scale.place_ruler(InsolationRuler)


for window in windows:
    scale = InsolationScale(doc, palette, step=step, day=day)
    scale.place(window, intersector)
    total, range = scale.range

    values = {
        InsolationRange: range,
        Insolation: round(total, 2) * 3600
    }
    set_lookup(window, values)

    shape, message = scale.show()
    if shape: set_lookup(shape, values)

transaction.Commit()

OUT = res
