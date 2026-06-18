from math import pi, atan2, sin, cos
from Autodesk.Revit.DB import XYZ

class Vector(object):
    def __init__(self, xyz):
        self.xyz = xyz
        # Angle between self and XYZ(0, 1, 0)
        self.direction = atan2(self.xyz.X, self.Y)  # note: x,y swapped because reference is +Y
        if self.direction < 0: self.direction += 2*pi

    @classmethod
    def by_angle(cls, angle):
        xyz = XYZ(
            sin(angle),
            cos(angle),
            0
        )
        return Vector(xyz)