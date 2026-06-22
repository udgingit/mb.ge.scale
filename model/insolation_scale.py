from datetime import datetime
from math import sin, cos, degrees, radians, sqrt, pi, asin, atan2

from System.Collections.Generic import List
from Autodesk.Revit.DB import (
    ElementId, BuiltInCategory,
    XYZ, Plane, Line, DirectShape, GeometryObject,
    BRepBuilder, BRepBuilderSurfaceGeometry, BRepType, BRepBuilderEdgeGeometry, BRepBuilderOutcome,
    Transform
)
from Autodesk.Revit.Exceptions import ArgumentException
from Autodesk.Revit.UI import TaskDialog

from .object_location import ObjectLocation
from .sector import Sector
from .sun_ray import SunRay
from util import xyz_to_direction, direction_to_xyz, show_ray

class InsolationScale(Sector):
    length = 25000/304.8
    approximately = True
    hour_start = 7
    hour_end = 24 - hour_start
    step = 0.25
    

    def __init__(self, doc, day='22.03'):

        self.doc = doc
        # Ordinal number of the day in the year
        self.day = datetime.strptime(day, '%d.%m').timetuple().tm_yday

        # Object geographical location
        self.location = ObjectLocation(self.doc)

        hours = [self.hour_start + i * self.step for i in range(int((self.hour_end-self.hour_start) / self.step) + 1)]
        self.ruler = [
            SunRay(self, float(hour))
            for hour in hours
        ]
        self.sector = 2*pi - self.ruler[-1].direction + self.ruler[0].direction

        super().__init__(self.location.south, self.sector)

        self.origin = XYZ()
        self.location.latitude = self.location.latitude
        self.normal = XYZ(
            -self.location.north.X * cos(self.location.latitude),
            -self.location.north.Y * cos(self.location.latitude),
            -sin(self.location.latitude)
        )
        self.plane = Plane.CreateByNormalAndOrigin(self.normal, self.origin)

        for current in self.ruler:
            show_ray(self.doc, self.origin, current.sun, self.plane)

    @property
    def solar_declination(self):
        # Solar declination
        if self.approximately:
            return radians(
                23.45 * sin(radians(360.0 * (284 + self.day) / 365.0))
            )
        
        B = radians(360.0 * (self.day - 81) / 365.0)
        self.declination = radians(
            0.006918
            - 0.399912 * cos(B)
            + 0.070257 * sin(B)
            - 0.006758 * cos(2 * B)
            + 0.000907 * sin(2 * B)
            - 0.002697 * cos(3 * B)
            + 0.00148  * sin(3 * B)
        )    
        
    def show_ruler_palne(self):
        plane = Plane.CreateByNormalAndOrigin(XYZ(0, 0, 1), XYZ(0, 0, 0))
        for current in self.ruler:
            
            show_ray(self.doc, XYZ(0, 0, 0), current.xyz, plane)


    def show_ruler(self):

        self.shape = None
        builder = BRepBuilder(BRepType.OpenShell)

        face = BRepBuilderSurfaceGeometry.Create(self.plane, None)
        
        
        material_id = ElementId(323956)
        

        for i in range(len(self.ruler)-1):
            face_id = builder.AddFace(face, False) #False - orientations agree
            builder.SetFaceMaterialId(face_id, material_id)
            loop_id = builder.AddLoop(face_id)

            left = self.ruler[i+1].sun
            right = self.ruler[i].sun

            a = self.origin
            c = self.origin.Add(left.Multiply(self.length))
            b = self.origin.Add(right.Multiply(self.length))

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

        self.shape = DirectShape.CreateElement(self.doc, ElementId(BuiltInCategory.OST_GenericModel))
        
        result = builder.GetResult()
        result = List[GeometryObject]([result])
        self.shape.SetShape(result)           
            