from math import pi, atan2, sin, cos, degrees
from Autodesk.Revit.DB import XYZ, Transform
from Autodesk.Revit.UI import TaskDialog

from util import direction_to_xyz, xyz_to_direction


class Vector(object):
    def __init__(self, source):
        if type(source) is XYZ:
            self.xyz = source
            # Angle between self and XYZ(0, 1, 0)
            self.direction = xyz_to_direction(self.xyz)

        elif type(source) is float:
            self.direction = source
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

    def rotated(self, angle):
        rotation = Transform.CreateRotation(
            XYZ.BasisZ,
            angle
        )
        xyz = rotation.OfVector(self.xyz).Normalize()
        return xyz_to_direction(xyz)
    
    def rotate(self, angle):
        self = self.rotated(self, angle)
    
    def __getattr__(self, name):
        return getattr(self.xyz, name)        

    @property
    def direction_deg(self):
        return degrees(self.direction)
    
    def show(self):
        TaskDialog.Show(
            'Vector',
            'Angle = %f' % self.direction_deg
        )
