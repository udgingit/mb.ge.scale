from math import sin, cos, atan2, pi
from Autodesk.Revit.DB import Transform, XYZ, Line, SketchPlane


def show_ray(doc, origin, vector, plane, length=5000/304.8):
    sketch_plane = SketchPlane.Create(doc, plane)
    line = Line.CreateBound(origin, origin.Add(vector.Multiply(length)))
    doc.Create.NewModelCurve(line, sketch_plane)


def direction_to_xyz(
        angle: float,
        default: XYZ = XYZ.BasisY) -> XYZ:
    """
    Converts an angular direction into a normalized Revit XYZ vector.

    The function rotates the specified reference vector around the global
    Z axis by the given angle and returns the resulting unit vector.

    Angles are measured counter-clockwise when looking in the positive
    Z direction (right-hand rule used by Revit).

    Parameters
    ----------
    angle : float
        Rotation angle in radians.
        Any value is accepted. Angles outside the range [0, 2π) are
        handled naturally by the rotation transform.

    default : Autodesk.Revit.DB.XYZ, optional
        Reference direction corresponding to zero angle.
        Defaults to XYZ.BasisY (0, 1, 0).

    Returns
    -------
    Autodesk.Revit.DB.XYZ
        Normalized vector obtained by rotating `default` around
        XYZ.BasisZ by `angle`.

    Examples
    --------
    Using the default reference direction (North / +Y):

    >>> direction_to_xyz(0)
    XYZ(0, 1, 0)

    >>> direction_to_xyz(pi / 2)
    XYZ(1, 0, 0)

    >>> direction_to_xyz(pi)
    XYZ(0, -1, 0)

    >>> direction_to_xyz(3 * pi / 2)
    XYZ(-1, 0, 0)

    Using a custom reference direction:

    >>> direction_to_xyz(pi / 2, XYZ.BasisX)
    XYZ(0, 1, 0)

    Notes
    -----
    The function is the inverse of obtaining a planar direction angle via:

        XYZ.BasisY.AngleOnPlaneTo(vector, XYZ.BasisZ)

    provided that `vector` lies in the XY plane.

    Coordinate system:

              Y+
              0°
               ↑
               |
    270° <-----+-----> 90°
               |
               ↓
             180°

    """    
    
    rotation = Transform.CreateRotation(
        XYZ.BasisZ,
        angle
    )
    return rotation.OfVector(default).Normalize()

def xyz_to_direction(
        vector: XYZ,
        default: XYZ = XYZ.BasisY) -> float:
    """
    Converts a planar Revit XYZ vector into a directional angle.

    The returned angle represents the counter-clockwise rotation from
    `reference` to `vector`, measured about the global Z axis according
    to Revit's right-hand rule.

    Parameters
    ----------
    vector : Autodesk.Revit.DB.XYZ
        Input direction vector.
        The vector is expected to lie in the XY plane.
        Its length is irrelevant; it will be normalized internally.

    reference : Autodesk.Revit.DB.XYZ, optional
        Reference direction corresponding to zero angle.
        Defaults to XYZ.BasisY (0, 1, 0).

    Returns
    -------
    float
        Direction angle in radians in the range [0, 2π).

    Examples
    --------
    >>> xyz_to_direction(XYZ.BasisY)
    0.0

    >>> xyz_to_direction(XYZ.BasisX)
    1.5707963267948966

    >>> xyz_to_direction(XYZ(0, -1, 0))
    3.141592653589793

    >>> xyz_to_direction(XYZ(-1, 0, 0))
    4.71238898038469

    Using a custom reference direction:

    >>> xyz_to_direction(XYZ.BasisY, XYZ.BasisX)
    1.5707963267948966

    Notes
    -----
    This function is the inverse of:

        direction_to_xyz(angle, reference)

    up to floating-point precision.

    Coordinate system with the default reference (XYZ.BasisY):

              Y+
              0°
               ↑
               |
    270° <-----+-----> 90°
               |
               ↓
             180°

    Raises
    ------
    ValueError
        If the vector has zero length.
    """
    vector = vector.Normalize()

    return default.AngleOnPlaneTo(
        vector,
        XYZ.BasisZ
    )


"""class AngleVector(object):
    def __init__(self, default=XYZ(0, 1, 0)):
        self.default = default

    def to_vector(angle):
        return XYZ(
            sin(angle),
            cos(angle),
            0
        )"""
def hours_to_string(hours):
    minutes = hours * 60
    hours = int(minutes/60)
    minutes = minutes%60
    return "%d' %d ''" % (hours, minutes)