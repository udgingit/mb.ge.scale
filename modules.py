import os
import sys
from Autodesk.Revit.UI import TaskDialog

project_dir = sys.path[-1]

library = os.path.abspath(os.path.join(project_dir, '..', '.lib'))
if library not in sys.path: sys.path.append(library)

internal_modules = (
    'internal.context',
    'model',
    'util'
)

for name in list(sys.modules):
    if any(
        name == current
        or name.startswith('%s.' % current)
        for current in internal_modules
    ):
        del sys.modules[name]
