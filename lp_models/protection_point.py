from math import sqrt

from Autodesk.Revit.DB import XYZ, Options, ViewDetailLevel, Solid, PlanarFace

from lp_utils import get_protection_radius

class ProtectionPoint(object):
    def __init__(self, surface, holder, index):
        if type(holder) is XYZ:
            self.point = holder
        else:
            self.point = self.get_protection_point(holder)

        self.X, self.Y, self.Z = self.point.X, self.point.Y, self.point.Z
        self.surface = surface
        self.holder = holder
        self.xy = (
            self.X, self.Y,
        )
        self.index = index

        self.already_protected = False

    def is_protected(self):
        elevation = self.Z - self.surface.plane_elevation
        for other in self.surface.points:
            if other is self:
                continue
            
            if other.Z <= self.Z:
                continue
            
            protection_radius = get_protection_radius(other, elevation, self.surface.plane_elevation, self.surface.radius)
            d = sqrt((self.X - other.X)**2 + (self.Y - other.Y)**2)
            if d <= protection_radius:
                self.already_protected = True
                return True
            
        return False

    @classmethod
    def get_protection_point(cls, holder):
        point = holder.Location.Point
        current = point.Z
        options = Options()
        options.DetailLevel = ViewDetailLevel.Undefined
        protection_face = None
        geometry = holder.get_Geometry(options)
        for instance in geometry:
            instance_geometry = instance.GetInstanceGeometry()
            for solid in instance_geometry:
                if type(solid) is Solid:
                    for face in solid.Faces:
                        if type(face) is PlanarFace:
                            origin = face.Origin
                            if origin.Z >= current:
                                protection_face = face
                                current = origin.Z

        if face is not None:
            box = protection_face.GetBoundingBox()
            mid = (box.Min.Add(box.Max)).Multiply(0.5)
            point = protection_face.Evaluate(mid)

        return point
    
    @property
    def name(self):
        return f'<{self.holder.Id}>'
    
    @property
    def errors(self):
        if self.already_protected:
            return f'{self.name}: Is already protected'
