from math import sqrt, acos, copysign, pi

from Autodesk.Revit.DB import XYZ, IntersectionResultArray, SetComparisonResult
from Autodesk.Revit.UI import TaskDialog
from numpy import array, linalg, float64
from numpy import roots as square_roots


class Message(object):
    no_ground = 'No ground Point'
    collinear = 'Points are collinear'
    dropping = 'The sphere is dropping down'
    success = 'Success'


def find_sphere_center_by_three_points(
        points: tuple[XYZ, XYZ, XYZ],
        radius: float) -> tuple[str, XYZ]:
    """
    Compute the center of a sphere given three non-collinear points on its surface
    and a known radius.

    The function finds the circle defined by the three points and then determines
    the possible sphere centers lying along the normal to that circle's plane.
    Two solutions are possible; the one with the greater Z coordinate is returned.

    Args:
        points (tuple[XYZ, XYZ, XYZ]):
            An iterable of exactly three XYZ points (a, b, c) lying on the sphere surface.
        radius (float):
            Radius of the sphere.

    Returns:
        Tuple[str, Optional[XYZ]]:
            A tuple containing:
            - status message (e.g., success, collinear points, invalid roots)
            - the computed sphere center as XYZ, or None if no valid solution

    Notes:
        - If the three points are collinear, the sphere center is undefined.
        - If the quadratic equation has no real roots, no valid sphere exists
          for the given radius and points.
        - Uses least squares to compute the circle center in 3D."""
    
    a, b, c = points
    ab = b.Subtract(a); ac = c.Subtract(a)
    normal = ab.CrossProduct(ac)
    if normal.GetLength() < 1e-9:
        return Message.collinear, None
    normal.Normalize()
    
    A = array([
        [ab.X, ab.Y, ab.Z],
        [ac.X, ac.Y, ac.Z]
    ])
    B = array([
        (b.DotProduct(b) - a.DotProduct(a)) / 2,
        (c.DotProduct(c) - a.DotProduct(a)) / 2
    ])
    
    C0, residuals, rank, s = linalg.lstsq(A, B, rcond=None)
    C0 = XYZ(*C0)
    
    roots = square_roots([
        normal.DotProduct(normal),
        2 * normal.DotProduct(C0.Subtract(a)),
        C0.Subtract(a).DotProduct(C0.Subtract(a)) - radius**2
    ])

    if type(roots[0]) is not float64:
        Message.dropping, None
    
    center = max(
        (
            C0.Add(normal.Multiply(roots[0])),
            C0.Add(normal.Multiply(roots[1]))
        ),
        key=lambda x: x.Z
    )
    return Message.success, center

def get_circle_by_two_points(points, center):
    # TODO extreme values, docs
    a, b = points
    A = a.Add(XYZ(0, 0, center.Z - a.Z))
    B = b.Add(XYZ(0, 0, center.Z - b.Z))
    AB = B.Subtract(A)
    AC = center.Subtract(A)
    proj = AB.Multiply(AC.DotProduct(AB) / AB.DotProduct(AB))
    circle_center = A.Add(proj)
    normal = (a.Subtract(circle_center)).CrossProduct(b.Subtract(circle_center)).Normalize()
    radius = circle_center.DistanceTo(a)
    return circle_center, normal, radius

def get_protection_radius(point, elevation, plane_elevation, radius):
    # TODO extreme vars, docs
    hx = elevation
    H = point.Z - plane_elevation
    return sqrt(2 * radius * H - H**2) - sqrt(2 * radius * hx - hx**2)


def find_ground_point(points, plane, radius):
    a, b = points
    plane_elevation = plane.Origin.Z
    h1 = a.Z - plane_elevation
    r1 = sqrt(2 * radius * h1 - h1**2)
    h2 = b.Z - plane_elevation
    r2 = sqrt(2 * radius * h2 - h2**2)

    dx = b.X - a.X
    dy = b.Y - a.Y
    d = sqrt(dx**2 + dy**2)
        
    x = (r1**2 - r2**2 + d**2) / (2*d)
    h = sqrt(max(r1**2 - x**2, 0))
    AB = b.Subtract(a)
    perp = AB.CrossProduct(XYZ.BasisZ).Normalize()
    m = a.Add(AB.Multiply(x/d))
    c = m.Add(perp.Multiply(h))
    return XYZ(c.X, c.Y, 0)


def find_ground_points(points, plane, radius, debug=False):
    # TODO check if exists, docs
    a, b = points
    h = plane.Origin.Z
    if (a.Z - h) > radius or (b.Z - h) > radius:
        return Message.no_ground, None, None
    
    n = plane.Normal
    d = - n.DotProduct(plane.Origin)
    m = a.Subtract(b)
    u = n.CrossProduct(m)
    u2 = u.DotProduct(u)
    h1 = radius - d
    h2 = 0.5 * (a.DotProduct(a) - b.DotProduct(b))
    C0 = m.CrossProduct(u).Multiply(h1).Add\
        (u.CrossProduct(n).Multiply(h2))
    C0 = C0.Multiply(1.0/u2)

    vec = C0.Subtract(a)

    roots = square_roots([
        u2,
        2.0 * u.DotProduct(vec),
        vec.DotProduct(vec) - radius**2
    ])

    if type(roots[0]) is not float64:
        return Message.no_ground, None, None
    
    points = [C0.Add(u.Multiply(x)).Subtract(n.Multiply(radius)) for x in roots]
    for point, root in zip(points, roots):
        ap = point.Subtract(a)
        cross = m.X * ap.Y - m.Y * ap.X
        if cross > 0:
            center = C0.Add(u.Multiply(root))
            return Message.success, point, center

    return Message.no_ground, roots, C0


def order_cw(points):
    a, b, c = points
    orientation = (b.X - a.X) * (c.Y - a.Y) - (b.Y - a.Y) * (c.X - a.X)
    if orientation > 0: return
    else: points.reverse() # False if clockwise


def is_cw(points):
    a, b, c = points
    orientation = (b.X - a.X) * (c.Y - a.Y) - (b.Y - a.Y) * (c.X - a.X)
    if orientation > 0: return True
    else: return False


def find_arcs_intersection(arc1, arc2):
    result_array = IntersectionResultArray()
    result = arc1.Intersect(arc2, result_array)
    if result[0] == SetComparisonResult.Overlap:
        intersections = result[1]
        for intersection in intersections:
            point = intersection.XYZPoint
            if not point.IsAlmostEqualTo(arc1.GetEndPoint(0)):
                if not point.IsAlmostEqualTo(arc1.GetEndPoint(1)):
                    return point


def signed_angle(vector, ref=XYZ.BasisX):
    """
    Returns signed angle between ref and v in range [0, 2π)
    v, ref, normal: Autodesk.Revit.DB.XYZ
    """
    v1 = ref.Normalize()
    v2 = vector.Normalize()

    # Compute unsigned angle
    dot = v1.DotProduct(v2)
    # Clamp for numerical stability
    dot = max(-1.0, min(1.0, dot))
    angle = acos(dot)

    # Determine sign using the normal direction
    cross = v1.CrossProduct(v2)
    sign = copysign(1.0, cross.DotProduct(XYZ.BasisZ))

    if sign < 0:
        angle = 2 * pi - angle

    return angle

def safe_action(foo):
    def wrapper(*args, **kwargs):
        try:
            return foo(*args, **kwargs)
        except Exception as exception:
            TaskDialog.Show(
                '%s - %s' % (foo.__name__, type(exception).__name__),
                str(exception)
            )
    return wrapper
