from datetime import datetime
from math import sin, cos, degrees, radians, sqrt, pi, asin, atan2
from Autodesk.Revit.DB import XYZ, Plane

from .object_location import ObjectLocation
from .sector import Sector
from util import vector_to_angle, show_ray

class InsolationScale(Sector):
    def __init__(self, doc, day='22.03'):
        self.doc = doc
        # Ordinal number of the day in the year
        self.day = datetime.strptime(day, '%d.%m').timetuple().tm_yday

        # Object geographical location
        self.location = ObjectLocation(self.doc)

        # Calculate Sun Vectors
        self.get_sun_vectors()
        
        south = self.location.north_angle + pi
        super().__init__(south, self.sector)

    def normalize_xy(self, v):
        v2 = XYZ(v.X, v.Y, 0)
        length = sqrt(v2.X**2 + v2.Y**2)
        if length == 0:
            raise Exception("North vector has zero XY length")
        return XYZ(v2.X / length, v2.Y / length, 0)


    def get_sun_vectors(self):
        """
        Returns sun vectors for 6:00-18:00 solar time.

        latitude_deg: широта в градусах, например 50.45
        north_vector: вектор севера в координатах Revit
        """

        lat = self.location.latitude

        # 22 марта ≈ день года 81
        self.day = 81

        # solar declination
        decl_deg = 23.45 * sin(radians(360.0 * (284 + self.day) / 365.0))
        decl = radians(decl_deg)

        up = XYZ.BasisZ
        north = self.normalize_xy(self.location.north)

        # East = North x Up
        east = north.CrossProduct(up).Normalize()

        self.ruler = list()

        for hour in range(8, 17):
            # solar hour angle
            H = radians(15.0 * (hour - 12.0))

            # altitude
            sin_alt = (
                sin(lat) * sin(decl) +
                cos(lat) * cos(decl) * cos(H)
            )

            alt = asin(sin_alt)
            cos_alt = cos(alt)

            # azimuth from north, clockwise
            sin_A = (-cos(decl) * sin(H)) / cos_alt
            cos_A = (
                cos(lat) * sin(decl) -
                sin(lat) * cos(decl) * cos(H)
            ) / cos_alt

            A = atan2(sin_A, cos_A)

            # horizontal projection
            horizontal = (
                east.Multiply(sin(A)).Add(
                north.Multiply(cos(A)))
            ).Normalize()

            # full 3D vector to sun
            sun_vector = (
                horizontal.Multiply(cos_alt).Add(
                up.Multiply(sin(alt)))
            ).Normalize()

            self.ruler.append({
                "hour": hour,
                "azimuth_deg": degrees(A) % 360,
                "altitude_deg": degrees(alt),
                "horizontal_vector": horizontal,
                "sun_vector": sun_vector
            })

        a = self.ruler[-1]['horizontal_vector']
        b = self.ruler[0]['horizontal_vector']
        self.sector = vector_to_angle(a, None) - vector_to_angle(b, None)

    def show_ruler(self):
        for current in self.ruler:
            vector = current['horizontal_vector']
            plane = Plane.CreateByNormalAndOrigin(XYZ(0, 0, 1), XYZ(0, 0, 0))
            show_ray(self.doc, XYZ(0, 0, 0), vector, plane)