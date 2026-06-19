from datetime import datetime
from math import sin, cos, degrees, radians, sqrt, pi, asin, atan2
from Autodesk.Revit.DB import XYZ, Plane
from Autodesk.Revit.UI import TaskDialog

from .object_location import ObjectLocation
from .sector import Sector
from .sun_ray import SunRay
from util import xyz_to_direction, direction_to_xyz, show_ray

class InsolationScale(Sector):
    solar_declination = radians(23.45)

    def __init__(self, doc, day='22.03'):
        self.doc = doc
        # Ordinal number of the day in the year
        self.day = datetime.strptime(day, '%d.%m').timetuple().tm_yday

        # Object geographical location
        self.location = ObjectLocation(self.doc)

        # Solar declination
        B = radians(360.0 * (self.day - 81) / 365.0)
        self.declination = (
            0.006918
            - 0.399912 * cos(B)
            + 0.070257 * sin(B)
            - 0.006758 * cos(2 * B)
            + 0.000907 * sin(2 * B)
            - 0.002697 * cos(3 * B)
            + 0.00148  * sin(3 * B)
        )     
        #self.calculate_sun_vectors()
        self.ruler = [
            SunRay(self, float(hour))
            for hour in range(6, 19)
        ]
        self.sector = 2*pi - self.ruler[-1].direction + self.ruler[0].direction

        super().__init__(self.location.south, self.sector)


    def calculate_sun_vectors(self):
        """
        Returns sun vectors for 6:00-18:00 solar time.

        latitude_deg: широта в градусах, например 50.45
        north_vector: вектор севера в координатах Revit
        """

        # Solar declination
        B = radians(360.0 * (self.day - 81) / 365.0)
        declination = (
            0.006918
            - 0.399912 * cos(B)
            + 0.070257 * sin(B)
            - 0.006758 * cos(2 * B)
            + 0.000907 * sin(2 * B)
            - 0.002697 * cos(3 * B)
            + 0.00148  * sin(3 * B)
        )        

        self.ruler = list()

        for hour in range(4, 21):
            # Solar hour angle
            H = radians(15.0 * (hour - 12.0))

            # Altitude
            altitude = asin(
                sin(self.location.latitude) * sin(declination) +
                cos(self.location.latitude) * cos(declination) * cos(H)                
            )

            # Azimuth from north, clockwise
            sin_A = (-cos(declination) * sin(H)) / cos(altitude)
            cos_A = (
                cos(self.location.latitude) * sin(declination) -
                sin(self.location.latitude) * cos(declination) * cos(H)
            ) / cos(altitude) 

            A = atan2(sin_A, cos_A)

            # Horizontal projection
            horizontal = direction_to_xyz(self.location.north.direction - A)

            # full 3D vector to sun
            sun_vector = (
                horizontal.Multiply(cos(altitude)).Add(
                XYZ.BasisZ.Multiply(sin(altitude)))
            ).Normalize()

            self.ruler.append({
                "hour": hour,
                "azimuth_deg": degrees(A) % 360,
                "altitude_deg": degrees(altitude),
                "horizontal_vector": horizontal,
                "sun_vector": sun_vector
            })

        a = self.ruler[-1]['horizontal_vector']
        b = self.ruler[0]['horizontal_vector']
        self.sector = 2*pi - (xyz_to_direction(a) - xyz_to_direction(b))

    def show_ruler(self):
        for current in self.ruler:
            plane = Plane.CreateByNormalAndOrigin(XYZ(0, 0, 1), XYZ(0, 0, 0))
            show_ray(self.doc, XYZ(0, 0, 0), current.xyz, plane)
            