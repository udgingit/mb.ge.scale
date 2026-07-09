from datetime import datetime
from math import sin, cos, degrees, radians, sqrt, pi, asin, atan2, tan, atan

from System.Collections.Generic import List
from Autodesk.Revit.DB import (
    FilteredElementCollector, FamilySymbol, AnnotationSymbol, ElementId, BuiltInCategory, BuiltInParameter,
    XYZ, Plane, Line, DirectShape, GeometryObject,
    BRepBuilder, BRepBuilderSurfaceGeometry, BRepType, BRepBuilderEdgeGeometry, BRepBuilderOutcome,
    ElementTransformUtils,
)
from Autodesk.Revit.Exceptions import ArgumentException
from Autodesk.Revit.UI import TaskDialog

from .object_location import ObjectLocation
from .sector import Sector
from .sun_ray import SunRay
from .vector import Vector
from .sun_sectors import SunSectors
from .sun_sector_groups import SunSectorGroups
from util import show_ray, hour_to_string, detect_intersection


class InsolationScale(Sector):
    length = 25000/304.8
    approximately = False
    start_hour = 7

    def __init__(self,
                 doc,
                 materials,  # dictionary with materials map
                 step=15,  # minutes between two SunRays
                 day='22.03',  # day of the year
                 category=BuiltInCategory.OST_Mass  # geometry shape Category
        ):
        self.doc = doc
        self.materials = materials
        self.category_id = ElementId(category)

        # Ordinal number of the day in the year
        self.day = datetime.strptime(day, '%d.%m').timetuple().tm_yday

        # Object geographical location
        self.location = ObjectLocation(self.doc)

        self.rays = self.get_rays(
            self.start_hour + i * step/60
            for i in range(int((24 - 2*self.start_hour) * 60 / step) + 1)
        )
        
        start = self.rays[-1]
        angle = self.location.south.direction - start.direction
        super().__init__( # TODO think about so complicated inheritance
            self.location.south,
            angle
        )

    def place(self, holder, intersector):
        self.intersector = intersector  # View3D-depended intersector created before
        self.holder = holder  # related Window
        self.host = holder.Host  # related Wall

        # Place scale to the window center
        height = holder.Symbol.get_Parameter(BuiltInParameter.FAMILY_HEIGHT_PARAM).AsDouble()
        self.origin = holder.Location.Point.Add(XYZ(0, 0, height/2))

        # Define window review limits
        depth = self.host.Width
        width = holder.Symbol.get_Parameter(BuiltInParameter.FURNITURE_WIDTH).AsDouble()
        angle = atan(width/depth) # half of the full window review

        window_direction = Vector(holder.FacingOrientation)
        window_direction.rotate(pi)
        window_scale = Sector(window_direction, angle)
        
        # Filter rays by window limits
        self.rays = [
            current for current in self.rays
            if window_scale.contains(current)
        ]

        # Add window limits to rays
        start, end = window_scale.limits

        if end.inside(self.limits): self.rays.insert(0, SunRay(self, end))
        if start.inside(self.limits): self.rays.append(SunRay(self, start))

        # Create SunSectors scope
        self.sectors = SunSectors(self)

        # Create SunSector groups
        self.groups = SunSectorGroups(self)

    def show(self):
        if not self.groups: return None, 'Empty Scale'
        self.shape = None
        builder = BRepBuilder(BRepType.OpenShell)

        face = BRepBuilderSurfaceGeometry.Create(self.plane, None)

        for group in self.groups:
            material_id = self.materials[group.state]
            for sector in group:
                left = sector.end.sun; right = sector.start.sun

                face_id = builder.AddFace(face, False) #False - orientations agree
                builder.SetFaceMaterialId(face_id, material_id)

                loop_id = builder.AddLoop(face_id)

                o = self.origin
                a = self.origin.Add(left.Multiply(self.length))
                b = self.origin.Add(right.Multiply(self.length))

                self.edges = (
                    Line.CreateBound(o, b),
                    Line.CreateBound(b, a),
                    Line.CreateBound(a, o)
                )

                for edge in self.edges:
                    edge = BRepBuilderEdgeGeometry.Create(edge)
                    edge_id = builder.AddEdge(edge)
                    try:
                        builder.AddCoEdge(loop_id, edge_id, False)
                    except ArgumentException:
                        return None, 'Edge exception'

                try:
                    builder.FinishLoop(loop_id) 
                except ArgumentException:
                    return None, 'Loop exception'
        
                builder.FinishFace(face_id)

        if builder.Finish() == BRepBuilderOutcome.Failure:
            return None, 'Finish exception'

        self.shape = DirectShape.CreateElement(self.doc, self.category_id)
        
        result = builder.GetResult()
        result = List[GeometryObject]([result])
        self.shape.SetShape(result)
        
        return self.shape, None
            
    def show_rays(self):
        plane = Plane.CreateByNormalAndOrigin(XYZ(0, 0, 1), XYZ(0, 0, 0))
        for current in self.rays:
            show_ray(self.doc, XYZ(0, 0, 0), current.xyz, plane)

    def get_rays(self, hours):
        return [
            SunRay(self, float(hour))
            for hour in hours
        ]
    
    @property
    def solar_declination(self):
        # Solar declination
        if self.approximately:
            return radians(
                23.45 * sin(radians(360.0 * (284 + self.day) / 365.0))
            )
        
        B = radians(360.0 * (self.day - 81) / 365.0)
        return radians(
              0.006918
            - 0.399912 * cos(B)
            + 0.070257 * sin(B)
            - 0.006758 * cos(2 * B)
            + 0.000907 * sin(2 * B)
            - 0.002697 * cos(3 * B)
            + 0.001480 * sin(3 * B)
        )    

    @property
    def normal(self):
        return XYZ(
            -self.location.north.X * cos(self.location.latitude),
            -self.location.north.Y * cos(self.location.latitude),
            -sin(self.location.latitude)
        )
    
    @property
    def plane(self):
        return Plane.CreateByNormalAndOrigin(self.normal, self.origin)
    
    @property
    def range(self):
        return self.groups.range
    
    def place_ruler(self, name):
        symbol = next((
            symbol for symbol in
            FilteredElementCollector(self.doc).OfClass(FamilySymbol)
            if symbol.FamilyName == name
        ), None)
        if not symbol: return

        for hour in range(13, 18):
            ray = SunRay(self, hour)
            current = ray.direction - self.location.north.direction
            parameter_name = 'Hour %d' % hour
            parameter = symbol.LookupParameter(parameter_name)
            if parameter: parameter.Set(current)
        
        annotations = [
            annotation for annotation in FilteredElementCollector(self.doc)
                .OfCategory(BuiltInCategory.OST_GenericAnnotation)
                .WhereElementIsNotElementType()
                .ToElements()
            if annotation.Symbol.Id == symbol.Id
        ]
        for annotation in annotations:
            transform = annotation.GetTransform()
            y = transform.BasisY

            current = y.AngleOnPlaneTo(XYZ.BasisY, XYZ.BasisZ)
            target = self.location.north.direction

            axis = Line.CreateUnbound(annotation.Location.Point, XYZ.BasisZ)

            ElementTransformUtils.RotateElement(
                self.doc,
                annotation.Id,
                axis,
                target + current
            )
