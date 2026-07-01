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

from Autodesk.Revit.UI import TaskDialog, ExternalCommandData
from RevitServices.Transactions import TransactionManager
from System.Collections.Generic import List




from math import pi, atan, atan2, degrees, sin, asin, cos, radians, sqrt
from Autodesk.Revit.DB import SketchPlane, Arc, Line, Transform, BRepBuilder, BRepType, BRepBuilderSurfaceGeometry, BRepBuilderEdgeGeometry
from Autodesk.Revit.DB import BRepBuilderOutcome, DirectShape, GeometryObject
from Autodesk.Revit.Exceptions import *


from internal.context import Context # Revit Model context

context = Context(revit)
doc = context.doc

from model import InsolationScale, Sector
from util import show_ray
res = dict()


# TODO define, how the window height is defined
LENGTH = 10000
def show_point(doc, point, radius=1/304.7):
    plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, point)
    sketch_plane = SketchPlane.Create(doc, plane)
    arc = Arc.Create(point, radius, 0, 2*pi, XYZ.BasisX, XYZ.BasisY)
    doc.Create.NewModelCurve(arc, sketch_plane)

    

def rotate_vector(vector, axis, angle):
    v = XYZ(vector.X, vector.Y, vector.Z)
    transform = Transform.CreateRotation(axis, angle)
    return transform.OfVector(v)

class InsScale(Sector):
    angle = pi/3 # 60° between ground plane and direction to the Sun

    def project(self, point):
        denom = self.normal.DotProduct(XYZ.BasisZ)
        t = self.normal.DotProduct(self.plane.Origin.Subtract(point)) / denom
        return point.Add(XYZ.BasisZ.Multiply(t))    
    
    def __init__(self, doc, holder):
        self.doc = doc
        self.window = holder # Window
        
        # Center point of the window
        origin = holder.Location.Point
        height = holder.Symbol.get_Parameter(BuiltInParameter.FAMILY_HEIGHT_PARAM).AsDouble()
        self.origin = origin.Add(XYZ(0, 0, height/2))

        # Align to the window orientation
        self._axis = rotate_vector(
            XYZ.BasisY,
            XYZ.BasisZ,
            holder.Location.Rotation + pi
        )

        self.wall_axis = rotate_vector(
            XYZ.BasisY,
            XYZ.BasisZ,
            holder.Location.Rotation - pi/2            
        )

        # tilted axis lying in the scale plane
        self.rot_axis = rotate_vector(
            self._axis,
            self.wall_axis,
            -self.angle
        )

        # plane normal
        self.normal = self.wall_axis.CrossProduct(self.rot_axis).Normalize()

        self.plane = Plane.CreateByNormalAndOrigin(
            self.normal,
            self.origin
        )

        host = holder.Host
        depth = host.Width
        width = holder.Symbol.get_Parameter(BuiltInParameter.FURNITURE_WIDTH).AsDouble()
        angle = atan(width/depth)*2 # half if the full scale angle

        self.direction_angle = atan2(self._axis.X, self._axis.Y)  # note: x,y swapped because reference is +Y
        if self.direction_angle < 0: self.direction_angle += 2*pi


        #self.start = rotate_vector(self._axis, XYZ.BasisZ, -angle)
        #self.end = rotate_vector(self._axis, XYZ.BasisZ, angle)
        super().__init__(self.direction_angle, angle)



        """if holder.Id.IntegerValue == 327323:
            b = self.origin.Add(self.end.Multiply(LENGTH*2.5/304.8))
            TaskDialog.Show('_deb', str(b))
            b = self.project(b)
            TaskDialog.Show('_deb', str(b))"""


    def show_axis(self):
        show_ray(self.doc, self.origin, self.axis, self.plane)
    
    def show_borders(self):
        show_ray(self.doc, self.origin, self.start, self.plane)
        show_ray(self.doc, self.origin, self.end, self.plane)


    def draw_surface(self):
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

        left = XYZ(
            sin(self.start),
            cos(self.start),
            0
        )

        right = XYZ(
            sin(self.end),
            cos(self.end),
            0
        )

        a = self.origin
        b = self.origin.Add(left.Multiply(LENGTH*2.5/304.8))
        c = self.origin.Add(right.Multiply(LENGTH*2.5/304.8))

        a = self.project(a)
        b = self.project(b)
        c = self.project(c)

        edge1 = Line.CreateBound(a, b)
        edge2 = Line.CreateBound(b, c)
        edge3 = Line.CreateBound(c, a)

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
lines = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Lines).WhereElementIsNotElementType().ToElementIds() 
for i in lines: doc.Delete(i)
w = doc.GetElement(ElementId(323466))

windows = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).WhereElementIsNotElementType().ToElements()

ins_ruler = InsolationScale(doc)
#ins_ruler.show()

"""from Autodesk.Revit.DB import XYZ

a = XYZ(0, -1, 0).AngleOnPlaneTo(
        XYZ.BasisY,
        XYZ.BasisZ
    )

TaskDialog.Show('_deb', str(degrees(a)))"""
o = InsolationScale(doc)
o.set_ruler(345853)

for w in windows:
    o = InsolationScale(doc)
    o.place(w)
    #o.show_axis()
    #o.show_borders()
    if o.ruler:
        o.show()

TransactionManager.Instance.TransactionTaskDone()




OUT = res
