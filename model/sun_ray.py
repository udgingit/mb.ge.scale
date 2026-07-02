from math import radians, degrees, sin, cos, asin, atan2, pi, tan, sqrt
from Autodesk.Revit.DB import XYZ
from Autodesk.Revit.UI import TaskDialog

from .vector import Vector


class SunRay(Vector):
    def __init__(self, scale, hour):
        declination = scale.solar_declination
        north = scale.location.north
        latitude = scale.location.latitude

        if type(hour) is float:
            self.hour = hour
            # Solar hour angle
            H = radians(15.0 * (hour - 12.0))

            # Altitude
            """altitude = asin(
                sin(latitude) * sin(declination) +
                cos(latitude) * cos(declination) * cos(H)                
            )

            # Azimuth from north, clockwise
            sin_A = (-cos(declination) * sin(H)) / cos(altitude)
            cos_A = (
                -cos(latitude) * sin(declination) -
                sin(latitude) * cos(declination) * cos(H)
            ) / cos(altitude)

            A = atan2(sin_A, cos_A)"""
            sin_A = - cos(declination) * sin(H)
            cos_A = - cos(latitude) * sin(declination)\
                    - sin(latitude) * cos(declination) * cos(H)

            A = atan2(sin_A, cos_A) # angle between north and ray counted CW


            super().__init__(north.direction - A)
         

        elif type(hour) is Vector:
            direction = hour.direction

            A = north.direction - direction
            sin_H = - sin(A) / cos(declination)

            cos_H = (- cos(A) - cos(latitude) * sin(declination)) /\
                (sin(latitude) * cos(declination))
            H = atan2(sin_H, cos_H)
            super().__init__(direction)

            self.hour = 12.0 + degrees(H) / 15.0


        altitude = asin(
            sin(latitude) * sin(declination) +
            cos(latitude) * cos(declination) * cos(H)                
        )   
        # full 3D vector to Sun
        self.sun = (
            self.xyz.Multiply(cos(altitude)).Add(
            XYZ.BasisZ.Multiply(sin(altitude)))
        ).Normalize()
       