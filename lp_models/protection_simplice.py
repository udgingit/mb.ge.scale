from math import pi, sqrt

from Autodesk.Revit.DB import (
    ElementId, BuiltInCategory,
    Arc, Plane, SketchPlane,  XYZ, DirectShape, RevolvedSurface, GeometryObject,
    BRepBuilder, BRepType, BRepBuilderSurfaceGeometry, BRepBuilderEdgeGeometry, BRepBuilderOutcome)
from Autodesk.Revit.Exceptions import ArgumentException
from System.Collections.Generic import List
from numpy import concatenate

from lp_utils import (find_arcs_intersection, find_ground_points,
                      find_sphere_center_by_three_points, order_cw,
                      signed_angle)

from .protection_edge import ProtectionEdge
from .protection_point import ProtectionPoint


class Simplice(object):
    message_edge_error = 'Cannot add the edge'
    message_loop_error = 'Cannot finish the loop'
    message_geometry_error = 'Cannot finish the geometry'
    message_surface_error = 'Cannot create revolved surface'

    def __init__(self, surface, points):
        self.surface = surface
        self.points = points
        self.coords = [point.point for point in self.points]
        self.indices = set([point.index for point in self.points])

        self.edges = list()
        self._errors = list()
        self._messages = list()
        self.is_valid = self.validate()

    def validate(self):
        return True
    
    def draw_edges(self, doc):
        for edge in self.edges: edge.draw(doc)

    def draw_points(self, doc, radius=250/304.8):
        for point in self.coords:
            plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, point)
            sketch_plane = SketchPlane.Create(doc, plane)
            arc = Arc.Create(point, radius, 0, 2*pi, XYZ.BasisX, XYZ.BasisY)
            doc.Create.NewModelCurve(arc, sketch_plane)
    
    def draw_surface(self, doc, material_id):
        self.shape = None
        builder = BRepBuilder(BRepType.OpenShell)

        try:
            face = BRepBuilderSurfaceGeometry.Create(self.full_surface, None)
        except ArgumentException:
            self._errors.append(self.message_surface_error)
            self.is_valid = False
            return
        face_id = builder.AddFace(face, False) #False - orientations agree
        builder.SetFaceMaterialId(face_id, material_id)
        loop_id = builder.AddLoop(face_id)

        for edge in self.edges:
            edge = BRepBuilderEdgeGeometry.Create(edge.arc)
            edge_id = builder.AddEdge(edge)
            try:
                builder.AddCoEdge(loop_id, edge_id, False)
            except ArgumentException:
                self._errors.append(self.message_edge_error)
                self.is_valid = False
                return

        try:
            builder.FinishLoop(loop_id) 
        except ArgumentException:
            self._errors.append(self.message_loop_error)
            self.is_valid = False
            return

        builder.FinishFace(face_id)
        if builder.Finish() == BRepBuilderOutcome.Failure:
            self._errors.append(self.message_geometry_error)
            self.is_valid = False
            return

        self.shape = DirectShape.CreateElement(doc, ElementId(BuiltInCategory.OST_GenericModel))
        
        result = builder.GetResult()
        result = List[GeometryObject]([result])
        self.shape.SetShape(result)

    @property
    def full_surface(self):
        return None
    
    @property
    def name(self):
        return ''.join(f'<{point.holder.Id}>' for point in self.points)
    
    @property
    def errors(self):
        return ''.join(f'{error}' for error in self._errors)
    
    @property
    def messages(self):
        return ''.join(f'{error}' for error in self._messages)
    
    def check_loop(self):
        for index in (0, 1, 2):
            one = self.edges[index]
            two = self.edges[(index + 1) % 3]
            intersection = find_arcs_intersection(
                one.arc,
                two.arc
            )
            if intersection is not None:
                one.split_from_start(intersection)
                two.split_to_end(intersection)
    

class SimpliceByThreeProtectionPoints(Simplice):
    def __init__(self, surface, points):
        super().__init__(surface, points)
        if not self.is_valid: return
        
        order_cw(self.points)
    
    def validate(self):
        result, self.center = find_sphere_center_by_three_points(self.coords, self.surface.radius)
        if self.center is None:
            self._messages.append(result)
            return False
        return True

    def build_edges(self):
        boundary = [
            (a, b)
            for a, b in zip(
                self.points,
                concatenate((self.points[1:], self.points[:1]))
            )
        ]
        
        for edge_points in boundary:
            adjacent = self.get_adjacent(edge_points)
            if adjacent is None:
                adjacent = SimpliceByTwoProtectionPoints(self.surface, self, edge_points)
                self.surface.simplices.append(adjacent)
                if not adjacent.is_valid:
                    edge = ProtectionEdge.by_two_points(self, edge_points)
                    self.edges.append(edge)
                    continue

            edge = ProtectionEdge.by_two_simplices(self, adjacent, edge_points)
            self.edges.append(edge)
        self.check_loop()

    def get_adjacent(self, edge_points):
        a, b = edge_points
        for simplice in self.surface.simplices:
            if simplice.is_valid:
                if simplice.indices != self.indices:
                    if a.index in simplice.indices:
                        if b.index in simplice.indices:
                            return simplice

    @property
    def full_surface(self):
        plane = Plane.CreateByNormalAndOrigin(XYZ(0, 0, 1), self.center)
        curve = Arc.Create(plane, self.surface.radius, 0, pi)

        return RevolvedSurface.Create(
            self.center,
            XYZ(1, 0, 0),
            curve
        )


class SimpliceByTwoProtectionPoints(Simplice):
    def __init__(self, surface, adjacent, points):
        self.adjacent = adjacent
        super().__init__(surface, points)
        if not self.is_valid: return
        #order_cw(self.points)

    def validate(self):
        #t = False
        #for point in self.points:
        #    if point.holder.Id.IntegerValue == 5114758:
        #        t = True

        result, ground_point, self.center = find_ground_points(
            [
                point.point for point in self.points
            ],
            self.surface.plane,
            self.surface.radius,
        )
        if ground_point is None:
            self._errors.append(result)
            return False
        
        self.coords = [point.point for point in self.points]
        self.coords.append(ground_point)
        self.ground_point = ProtectionPoint(self.surface, ground_point, None)
        return True
        
    def build_edges(self):
        self.edges.extend((
            ProtectionEdge.by_two_simplices(self, self.adjacent, (self.points[1], self.points[0])),
            ProtectionEdge.by_two_points(self, (self.points[0], self.ground_point)),
            ProtectionEdge.by_two_points(self, (self.ground_point, self.points[1]))
        ))
        #self.edges[0].arc =self.edges[0].arc.CreateReversed()
        #TODO reverse arc in edge constructor

    @property
    def full_surface(self):
        plane = Plane.CreateByNormalAndOrigin(XYZ(0, 0, 1), self.center)
        curve = Arc.Create(plane, self.surface.radius, 0, pi)

        return RevolvedSurface.Create(
            self.center,
            XYZ(1, 0, 0),
            curve
        )        


class SimpliceByOneProtectionPoint(Simplice):
    def __init__(self, surface, point):
        self.index = point.index
        super().__init__(surface, [point])
        if not self.is_valid: return
        self.build_edges()

    def validate(self):
        self.adjacent = list()
        for current in self.surface.simplices:
            if type(current) is SimpliceByTwoProtectionPoints:
                if current.is_valid:
                    if self.index in current.indices:
                        self.adjacent.append(current)
        if len(self.adjacent) != 2:
            return False
        return True
    
    def build_edges(self):
        self.plane_elevation = self.surface.plane_elevation
        point = self.points[0].point  
        self.O = XYZ(point.X, point.Y, self.plane_elevation)

        height = point.Z - self.plane_elevation
        protection_radius = sqrt(2 * self.surface.radius * height - height**2)

        for adjacent in self.adjacent:
            if adjacent.points[1].point.IsAlmostEqualTo(point):
                for edge in adjacent.edges:
                    if edge.a.IsAlmostEqualTo(adjacent.ground_point.point):
                        start_arc = edge.arc
                        start_ground = adjacent.ground_point.point
            if adjacent.points[0].point.IsAlmostEqualTo(point):
                for edge in adjacent.edges:
                    if edge.b.IsAlmostEqualTo(adjacent.ground_point.point):
                        end_arc = edge.arc
                        end_ground = adjacent.ground_point.point

        ground_bound = ProtectionEdge(
            self.surface,
            (start_ground, end_ground),
            self.O,
            XYZ(0, 0, 1),
            protection_radius
        )
        self.edges = (
            ProtectionEdge.by_arc(self.surface, start_arc.CreateReversed()),
            ground_bound,
            ProtectionEdge.by_arc(self.surface, end_arc.CreateReversed()),
        )

        v1 = start_ground.Subtract(self.O)
        v2 = end_ground.Subtract(self.O)
        a1 = signed_angle(v1)
        a2 = signed_angle(v2)
        if a2 < a1:
            a1 = a1-2*pi

        ground_bound.arc = Arc.Create(ground_bound.plane, protection_radius, a1, a2)

    @property
    def full_surface(self):
        return RevolvedSurface.Create(
            self.O,
            XYZ(0, 0, 1),
            self.edges[0].arc.CreateReversed()
        )            
