import os
import sys
import random

from Autodesk.Revit.DB import (
    Document,
    ElementId, BuiltInCategory, BuiltInParameter, ParameterElement,
    FilteredElementCollector, ElementFilter, ElementParameterFilter, ElementCategoryFilter,
    ParameterValueProvider, FilterStringRule, FilterStringEquals, LogicalOrFilter, LogicalAndFilter,
    Transaction,
    XYZ, Plane
)
from Autodesk.Revit.DB.Structure import StructuralType
from Autodesk.Revit.ApplicationServices import Application
from Autodesk.Revit.Exceptions import OperationCanceledException
from Autodesk.Revit.UI import TaskDialog, ExternalCommandData, UIApplication, UIDocument
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
from System.Collections.Generic import List
from System.Collections import ICollection
from System.Collections.ObjectModel import ObservableCollection
from System import Uri, UriKind
from System.IO import File, FileStream, FileMode, FileAccess, Path
from System.Windows import Window
from System.Windows.Markup import XamlReader
from System.Windows.Media.Imaging import BitmapImage

LENGTH = 10000

# TODO the surface doesn't need to be a triangle
# TODO math domain error in edge_by_two_simplices
# TODO errors messages
# NOTE: project_dir (path), revit (ExternalCommandData) and uiapp (UIApplication) are provided externally
# They must exist before this script runs
# Path to the project directory
project_dir: str = None
sys.path.append(project_dir)
# The Revit external command data object passed from C#
revit: ExternalCommandData = None
# Represents an active session of the Autodesk Revit UI
uiapp = revit.Application if revit else None  # type: UIApplication
# Returns the database level Application represented by this UI-level Application
app = uiapp.Application if uiapp else None  # type: Application
# Provides access to the currently active project
uidoc = uiapp.ActiveUIDocument if uiapp else None  # type: UIDocument
# Returns the database level document represented by this UI-level document
doc = uidoc.Document if uidoc else None  # type: Document
# Selected element IDs in the current document
sel = uidoc.Selection.GetElementIds() if uidoc else None  # type: ICollection
sys.path.append(r'c:\Users\yevhen.khlopeniuk\Documents\Script\.lib\internal')

from math import pi, atan, degrees
from Autodesk.Revit.DB import SketchPlane, Arc, Line, Transform, BRepBuilder, BRepType, BRepBuilderSurfaceGeometry, BRepBuilderEdgeGeometry
from Autodesk.Revit.DB import BRepBuilderOutcome, DirectShape, GeometryObject
from Autodesk.Revit.Exceptions import *

res = dict()

def show_point(doc, point, radius=1/304.7):
    plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, point)
    sketch_plane = SketchPlane.Create(doc, plane)
    arc = Arc.Create(point, radius, 0, 2*pi, XYZ.BasisX, XYZ.BasisY)
    doc.Create.NewModelCurve(arc, sketch_plane)

def show_ray(doc, origin, vector, plane, length=5000/304.8):
    sketch_plane = SketchPlane.Create(doc, plane)
    line = Line.CreateBound(origin, origin.Add(vector.Multiply(length)))
    doc.Create.NewModelCurve(line, sketch_plane)

class InsolationScale(object):
    def __init__(self, doc, window):
        self.doc = doc
        self.window = window
        
        # center point of the window
        origin = window.Location.Point
        height = window.Symbol.get_Parameter(BuiltInParameter.FAMILY_HEIGHT_PARAM).AsDouble() # TODO define, how is the window height defined
        self.origin = origin.Add(XYZ(0, 0, height/2))

        # align to window orientation
        angle_oy = window.Location.Rotation + pi
        transform = Transform.CreateRotation(XYZ.BasisZ, angle_oy)
        self.axis = transform.OfVector(XYZ.BasisY)

        # create scale plane
        angle_oz = pi/6 # 30° between wall anp plane
        angle_oz = pi/3 # 30° between wall anp plane
        
        horizontal_axis = Transform.CreateRotation( # mathes the wall orientation
            XYZ.BasisZ, pi/2
        ).OfVector(self.axis)

        self.axis = Transform.CreateRotation( # center scale axis
            horizontal_axis, angle_oz - pi/2
        ).OfVector(self.axis)

        self.normal = Transform.CreateRotation( # plane normal
            horizontal_axis, pi/2
        ).OfVector(self.axis)

        self.plane = Plane.CreateByNormalAndOrigin(self.normal, self.origin)

        host = window.Host
        depth = host.Width
        width = window.Symbol.get_Parameter(BuiltInParameter.FURNITURE_WIDTH).AsDouble()
        angle = atan(width/depth) # half if the full scale angle
        start = self.axis
        transform = Transform.CreateRotation(self.normal, angle)
        self.start = transform.OfPoint(start)
        end = self.axis
        transform = Transform.CreateRotation(self.normal, -angle)
        self.end = transform.OfPoint(end)

    def show_axis(self):
        show_ray(self.doc, self.origin, self.axis, self.plane)
    
    def show_borders(self):
        show_ray(self.doc, self.origin, self.start, self.plane)
        show_ray(self.doc, self.origin, self.end, self.plane)

    def draw_surface(self, num):
        self.shape = None
        builder = BRepBuilder(BRepType.OpenShell)

        try:
            face = BRepBuilderSurfaceGeometry.Create(self.plane, None)
        except ArgumentException:
            TaskDialog.Show('_deb', 'argumentexc')
            #self._errors.append(self.message_surface_error)
            #self.is_valid = False
        
        face_id = builder.AddFace(face, False) #False - orientations agree
        material_id = ElementId(323956)
        builder.SetFaceMaterialId(face_id, material_id)
        loop_id = builder.AddLoop(face_id)

        a = self.origin
        b = self.origin.Add(self.axis.Multiply(LENGTH/304.8))
        c = self.origin.Add(self.end.Multiply(LENGTH*2.5/304.8))
        d = self.origin.Add(self.start.Multiply(LENGTH*2.5/304.8))
        if num == 1:
            edge1 = Line.CreateBound(a, b)
            edge2 = Line.CreateBound(b, d)
            edge3 = Line.CreateBound(d, a)
        if num == 2:
            edge1 = Line.CreateBound(a, c)
            edge2 = Line.CreateBound(c, b)
            edge3 = Line.CreateBound(b, a)

        self.edges = (edge1, edge2, edge3)
        for edge in self.edges:
            edge = BRepBuilderEdgeGeometry.Create(edge)
            edge_id = builder.AddEdge(edge)
            try:
                builder.AddCoEdge(loop_id, edge_id, False)
            except ArgumentException:
                #self._errors.append(self.message_edge_error)
                #self.is_valid = False
                TaskDialog.Show('_deb', 'edge exc')
                return

        try:
            builder.FinishLoop(loop_id) 
        except ArgumentException:
            #self._errors.append(self.message_loop_error)
            #self.is_valid = False
            TaskDialog.Show('_deb', 'loop exc')
            return
  

        builder.FinishFace(face_id)
        if builder.Finish() == BRepBuilderOutcome.Failure:
            TaskDialog.Show('_deb', 'finish exc')
            #self._errors.append(self.message_geometry_error)
            #self.is_valid = False
            return

        self.shape = DirectShape.CreateElement(doc, ElementId(BuiltInCategory.OST_GenericModel))
        
        result = builder.GetResult()
        result = List[GeometryObject]([result])
        self.shape.SetShape(result)        
        





#transaction = Transaction(doc)
#transaction.Start('New transaction')
TransactionManager.Instance.EnsureInTransaction(doc);

generics = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_GenericModel).WhereElementIsNotElementType().ToElementIds() 
for i in generics: doc.Delete(i)
w = doc.GetElement(ElementId(323466))
windows = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).WhereElementIsNotElementType().ToElements()
for w in windows:
    o = InsolationScale(doc, w)
    o.show_axis()
    o.show_borders()
    o.draw_surface(1)
    o.draw_surface(2)

#origin = get_origin(w)
#show_point(doc, origin)
#vector = get_center_vector(w)
#show_ray(doc, origin, vector)
#start, end = get_side_vectors(w, vector)
#show_ray(doc, origin, start)
#show_ray(doc, origin, end)
#transaction.Commit()
TransactionManager.Instance.TransactionTaskDone();

res['result'] = degrees(0)

OUT = res
