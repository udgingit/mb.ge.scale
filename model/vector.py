from math import pi, atan2, sin, cos, degrees
from Autodesk.Revit.DB import XYZ, Transform
from Autodesk.Revit.UI import TaskDialog

from util import direction_to_xyz, xyz_to_direction


class Vector(object):
    def __init__(self, source):
        if type(source) is XYZ:
            self.xyz = source
            # Full angle between self and XYZ(0, 1, 0) counted counter-clockwise
            self.direction = xyz_to_direction(self.xyz)

        elif type(source) is float:
            self.direction = source % (2*pi) # direction must be in [0, 2π)
            self.xyz = direction_to_xyz(source)
        else:
            raise TypeError(
                'Vector source must be XYZ or float, got %s.' % type(source).__name__
            )

        self.verify()
    
    def verify(self):
        if abs(self.xyz.Z) > 1e-9:
            raise ValueError('Z coordinate must be 0.')

        if abs(self.xyz.GetLength() - 1.0) > 1e-9:
            raise ValueError('Vector is not normalized.')
        
        if self.direction >= 2*pi:
            raise ValueError('Invalid direction value %d.' % self.direction)

    def rotated(self, angle):
        rotation = Transform.CreateRotation(
            XYZ.BasisZ,
            angle
        )
        xyz = rotation.OfVector(self.xyz).Normalize()
        return Vector(xyz)
    
    def rotate(self, angle):
        self = self.rotated(angle)

    def inside(self, interval):
        start, end = (v.direction for v in interval)
        if start <= end:
            return start <= self.direction <= end
        else:
            return self.direction >= start or self.direction <= end
    
    def __getattr__(self, name):
        return getattr(self.xyz, name)        

    @property
    def direction_deg(self):
        return degrees(self.direction)
    
    def show(self):
        TaskDialog.Show(
            'Vector',
            'Angle = %f; %s' % (self.direction_deg, str(self.xyz))
        )
