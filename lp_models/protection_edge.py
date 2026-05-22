from math import sqrt

from Autodesk.Revit.DB import Plane, Arc, Line, SketchPlane

from lp_utils import get_circle_by_two_points


class ProtectionEdge(object):
    def __init__(self, surface, points, center, normal, radius):
        """
        Initializes a ProtectionEdge instance.

        Args:
            surface (ProtectionSurface): The surface that holds this edge.
            points (tuple): A 2-item tuple with edge start and end points
            center (XYZ): The center of base circle
            normal (XYZ): The normal vector of base Plane
            radius (XYZ): The base circle radius
        """        
        self.surface = surface
        self.a, self.b = points
        v1 = (self.a.Subtract(center))
        v2 = (self.b.Subtract(center))

        bisector = (v1.Add(v2)).Normalize()
        m = min(
            center.Add(bisector.Multiply(radius)),
            center.Add(bisector.Multiply(-radius)),
            key=lambda x: x.Z
        )

        self.plane = Plane.CreateByNormalAndOrigin(normal, center)
        self.arc = Arc.Create(self.a, self.b, m)
        self.line = Line.CreateBound(self.a, self.b)        


    @classmethod
    def by_two_simplices(cls, simplice, adjacent, edge_points):
        surface = simplice.surface
        normal = adjacent.center.Subtract(simplice.center)
        distance = normal.GetLength()
        if distance <1e-6:
            return ProtectionEdge.by_two_points(simplice, edge_points)
        else:
            center = simplice.center.Add(normal.Normalize().Multiply(distance/2))
            radius = sqrt(surface.radius**2 - (distance/2)**2)
            points = [point.point for point in edge_points]
            return ProtectionEdge(surface, points, center, normal, radius)
    
    @classmethod
    def by_two_points(cls, simplice, edge_points):
        surface = simplice.surface
        points = [point.point for point in edge_points]
        center, normal, radius = get_circle_by_two_points(points, simplice.center)
        return ProtectionEdge(surface, points, center, normal, radius)
    
    @classmethod
    def by_arc(cls, surface, arc):
        edge = ProtectionEdge(
            surface,
            [arc.GetEndPoint(0), arc.GetEndPoint(1)],
            arc.Center,
            arc.Normal,
            arc.Radius
        )
        edge.arc = arc
        return edge
        
    def split_from_start(self, point):
        start = self.arc.GetEndPoint(0)
        start_parameter = self.arc.GetEndParameter(0)
        split_parameter = self.arc.Project(point).Parameter
        middle_parameter = (start_parameter + split_parameter)/2
        middle = self.arc.Evaluate(middle_parameter, False)
        self.arc = Arc.Create(start, point, middle)

    def split_to_end(self, point):
        end = self.arc.GetEndPoint(1)
        end_parameter = self.arc.GetEndParameter(1)
        split_parameter = self.arc.Project(point).Parameter
        middle_parameter = (end_parameter + split_parameter)/2
        middle = self.arc.Evaluate(middle_parameter, False)
        self.arc = Arc.Create(point, end, middle)

        #TODO the same with line
        

    def draw(self, doc):
        sketch_plane = SketchPlane.Create(doc, self.plane)
        doc.Create.NewModelCurve(self.arc, sketch_plane)
