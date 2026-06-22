from math import radians, degrees, sin, cos, asin, atan2, pi
from Autodesk.Revit.DB import XYZ

from .vector import Vector


class SunRay(Vector):
    def __init__(self, scale, hour):
        declination = scale.solar_declination
        north = scale.location.north
        latitude = scale.location.latitude

        if type(hour) is float:
            # Solar hour angle
            H = radians(15.0 * (hour - 12.0))

            # Altitude
            altitude = asin(
                sin(latitude) * sin(declination) +
                cos(latitude) * cos(declination) * cos(H)                
            )

            # Azimuth from north, clockwise
            sin_A = (-cos(declination) * sin(H)) / cos(altitude)
            cos_A = (
                -cos(latitude) * sin(declination) -
                sin(latitude) * cos(declination) * cos(H)
            ) / cos(altitude) 

            A = atan2(sin_A, cos_A)

            super().__init__(north.direction - A)

            # full 3D vector to sun
            self.sun = (
                self.xyz.Multiply(cos(altitude)).Add(
                XYZ.BasisZ.Multiply(sin(altitude)))
            ).Normalize()
       