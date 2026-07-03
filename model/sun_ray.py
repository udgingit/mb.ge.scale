from math import radians, degrees, sin, cos, asin, atan2, pi, tan, sqrt
from Autodesk.Revit.DB import XYZ
from Autodesk.Revit.UI import TaskDialog

from .vector import Vector


class SunRay(Vector):
    def __init__(self, scale, route):
        declination = scale.solar_declination
        north = scale.location.north
        latitude = scale.location.latitude

        if type(route) in (float, int):
            self.hour = route

            # Solar hour angle
            H = radians(15.0 * (route - 12.0)) # H == 0 at 12 o'clock

            # not real sin and cos, but correct ratio
            sin_A = - cos(declination) * sin(H)
            cos_A = - cos(latitude) * sin(declination)\
                    - sin(latitude) * cos(declination) * cos(H)

            # Azimuth -- angle between north and ray counted CW
            A = atan2(sin_A, cos_A)

            direction = north.direction - A

        elif type(route) is Vector:
            direction = route.direction

            A = north.direction - direction

            sin_H = - sin(A) / cos(declination)
            cos_H = (- cos(A) - cos(latitude) * sin(declination)) /\
                (sin(latitude) * cos(declination))
            
            H = atan2(sin_H, cos_H)

            self.hour = 12.0 + degrees(H) / 15.0
        
        super().__init__(direction)

        # Altitude -- angle between SunVector and horizontal plane
        altitude = asin(
            sin(latitude) * sin(declination) +
            cos(latitude) * cos(declination) * cos(H)                
        )   
        # full 3D vector to Sun
        self.sun = (
            self.xyz.Multiply(cos(altitude)).Add(
            XYZ.BasisZ.Multiply(sin(altitude)))
        ).Normalize()
       