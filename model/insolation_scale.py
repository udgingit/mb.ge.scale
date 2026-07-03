from datetime import datetime
from math import sin, cos, degrees, radians, sqrt, pi, asin, atan2, tan, atan

from System.Collections.Generic import List
from Autodesk.Revit.DB import (
    ElementId, BuiltInCategory, BuiltInParameter,
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
from util import xyz_to_direction, direction_to_xyz, show_ray, hour_to_string


class InsolationScale(Sector):
    length = 25000/304.8
    approximately = False
    hour_start = 7
    hour_end = 24 - hour_start
    step = 0.25
    

    def __init__(self, doc, day='22.03'):

        self.doc = doc
        # Ordinal number of the day in the year
        self.day = datetime.strptime(day, '%d.%m').timetuple().tm_yday

        # Object geographical location
        self.location = ObjectLocation(self.doc)

        self.ruler = self.get_rays(
            self.hour_start + i * self.step
            for i in range(int((self.hour_end-self.hour_start) / self.step) + 1)

        )
        # TODO think about so complicated inheritance
        start = self.ruler[-1]
        angle = self.location.south.direction - start.direction
        super().__init__(
            self.location.south,
            angle
            )

    def get_rays(self, hours):
        return [
            SunRay(self, float(hour))
            for hour in hours
        ]
    
    def set_ruler(self, ruler_id):
        symbol = self.doc.GetElement(ElementId(ruler_id))
        hours = range(7, 18)
        ruler = self.get_rays(hours)
        for suffix, ray in enumerate(ruler, start=7):
            if suffix == 12: continue
            name = 'Hour %d' % suffix
            angle = ray.direction - self.location.north.direction
            parameter = symbol.LookupParameter(name)
            parameter.Set(angle)

        fam = self.doc.GetElement(ElementId(345855))
        transform = fam.GetTransform()
        y = transform.BasisY

        #current = atan2(y.X, y.Y)  # angle from global Y, CCW
        #if current < 0:
        #    current += 2 * pi
        current = 2*pi - y.AngleOnPlaneTo(XYZ(0, 1, 0), XYZ(0, 0, 1))
        target = self.location.north.direction

        delta = target - current

        delta = target - current
        loc = fam.Location
        axis = Line.CreateBound(
            loc.Point,
            loc.Point.Add(XYZ.BasisZ)
        )

        ElementTransformUtils.RotateElement(
            self.doc,
            fam.Id,
            axis,
            delta
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
    
    def place(self, holder):
        height = holder.Symbol.get_Parameter(BuiltInParameter.FAMILY_HEIGHT_PARAM).AsDouble()
        self.origin = holder.Location.Point.Add(XYZ(0, 0, height/2))

        host = holder.Host
        depth = host.Width
        width = holder.Symbol.get_Parameter(BuiltInParameter.FURNITURE_WIDTH).AsDouble()
        angle = atan(width/depth) # half of the full window review

        window_direction = Vector(holder.FacingOrientation)
        window_direction.rotate(pi)
        window_scale = Sector(window_direction, angle)
        
        self.ruler = [
            current for current in self.ruler
            if window_scale.contains(current)
        ]

        start, end = window_scale.limits

        if end.inside(self.limits): self.ruler.insert(0, SunRay(self, end))
        if start.inside(self.limits): self.ruler.append(SunRay(self, start))
        
        if self.ruler:
            rise, down = self.ruler[0].hour, self.ruler[-1].hour
            range = '%s÷%s' % (hour_to_string(rise), hour_to_string(down))
            total = down - rise
            info = '%s (%s)' % (range, hour_to_string(total))
        else:
            info = ''
            total = 0
            
        holder.LookupParameter('InsolationRange').Set(info)
        holder.LookupParameter('Insolation').Set(round(total, 2) * 3600)

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
            + 0.00148  * sin(3 * B)
        )    
        
    def show_rays(self):
        plane = Plane.CreateByNormalAndOrigin(XYZ(0, 0, 1), XYZ(0, 0, 0))
        for current in self.ruler:
            
            show_ray(self.doc, XYZ(0, 0, 0), current.xyz, plane)


    def show(self):

        self.shape = None
        builder = BRepBuilder(BRepType.OpenShell)

        face = BRepBuilderSurfaceGeometry.Create(self.plane, None)
        
        
        material_id = ElementId(323956)
        

        sectors = [
            (prev, cur)
            for prev, cur in zip(self.ruler, self.ruler[1:])
        ]

        #for i in range(len(self.ruler)-1):
        for current, next in sectors:
            face_id = builder.AddFace(face, False) #False - orientations agree
            builder.SetFaceMaterialId(face_id, material_id)
            loop_id = builder.AddLoop(face_id)

            #left = self.ruler[i+1].sun
            #right = self.ruler[i].sun
            left = next.sun
            right = current.sun

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

        self.shape = DirectShape.CreateElement(self.doc, ElementId(BuiltInCategory.OST_Mass))
        
        result = builder.GetResult()
        result = List[GeometryObject]([result])
        self.shape.SetShape(result)           
            