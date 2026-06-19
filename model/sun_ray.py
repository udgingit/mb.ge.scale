from math import radians, degrees, sin, cos, asin, atan2
from Autodesk.Revit.DB import XYZ

from .vector import Vector


class SunRay(Vector):
    def __init__(self, scale, hour):
        declination = scale.declination
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
                cos(latitude) * sin(declination) -
                sin(latitude) * cos(declination) * cos(H)
            ) / cos(altitude) 

            A = atan2(sin_A, cos_A)

            # Horizontal projection
            #self.horizontal = direction_to_xyz(self.location.north.direction - A)
            super().__init__(north.direction - A)

            # full 3D vector to sun
            sun_vector = (
                self.xyz.Multiply(cos(altitude)).Add(
                XYZ.BasisZ.Multiply(sin(altitude)))
            ).Normalize()

            """self.ruler.append({
                "hour": hour,
                "azimuth_deg": degrees(A) % 360,
                "altitude_deg": degrees(altitude),
                "horizontal_vector": horizontal,
                "sun_vector": sun_vector
            })    """        