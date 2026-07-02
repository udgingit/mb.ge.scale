from math import radians, degrees, sin, cos, asin, atan2, pi, tan
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

        if type(hour) is Vector:
            direction = hour.direction

            # A — тот же азимут, который в первой ветке используется здесь:
            # super().__init__(north.direction - A)
            A = north.direction - direction
            A = (A + pi) % (2 * pi) - pi

            # Решаем обратную задачу:
            # cos(A)*sin(H) - sin(A)*sin(latitude)*cos(H)
            # = sin(A)*cos(latitude)*tan(declination)

            a = cos(A)
            b = -sin(A) * sin(latitude)
            c = sin(A) * cos(latitude) * tan(declination)

            R = sqrt(a * a + b * b)

            if R == 0:
                H = 0.0
            else:
                q = c / R
                q = max(-1.0, min(1.0, q))

                gamma = atan2(b, a)

                H1 = asin(q) - gamma
                H2 = pi - asin(q) - gamma

                H1 = (H1 + pi) % (2 * pi) - pi
                H2 = (H2 + pi) % (2 * pi) - pi

                candidates = [H1, H2]

                # Нам нужен диапазон 6:00–18:00:
                # H от -90° до +90°
                candidates = [
                    h for h in candidates
                    if -pi / 2 <= h <= pi / 2
                ] or [H1, H2]

                # В твоей системе:
                # A > 0  — утро, H < 0
                # A < 0  — вечер, H > 0
                if abs(abs(A) - pi) < 1e-6:
                    H = min(candidates, key=lambda h: abs(h))
                elif A > 0:
                    H = min(candidates, key=lambda h: abs(h) if h <= 0 else abs(h) + 10)
                else:
                    H = min(candidates, key=lambda h: abs(h) if h >= 0 else abs(h) + 10)

            altitude = asin(
                sin(latitude) * sin(declination) +
                cos(latitude) * cos(declination) * cos(H)
            )

            super().__init__(direction)

            self.hour = 12.0 + degrees(H) / 15.0

        # full 3D vector to Sun
        self.sun = (
            self.xyz.Multiply(cos(altitude)).Add(
            XYZ.BasisZ.Multiply(sin(altitude)))
        ).Normalize()
       