from math import sin, cos, atan2
from Autodesk.Revit.DB import XYZ, Line, SketchPlane


def show_ray(doc, origin, vector, plane, length=5000/304.8):
    sketch_plane = SketchPlane.Create(doc, plane)
    line = Line.CreateBound(origin, origin.Add(vector.Multiply(length)))
    doc.Create.NewModelCurve(line, sketch_plane)

def angle_to_vector(angle):
    return XYZ(
        sin(angle),
        cos(angle),
        0
    )

def vector_to_angle(vector, default)    :
    return atan2(vector.X, vector.Y)  # note: x,y swapped because reference is +Y


class AngleVector(object):
    def __init__(self, default=XYZ(0, 1, 0)):
        self.default = default

    def to_vector(angle):
        return XYZ(
            sin(angle),
            cos(angle),
            0
        )