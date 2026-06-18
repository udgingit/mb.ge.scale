from math import pi, degrees


class Sector(object):
    empty_angle = 0.1
    
    @staticmethod
    def normalize(angle):
        return angle % (2*pi)

    @staticmethod
    def angle_diff(a, b):
        """
        Signed shortest difference a-b in [-π, π]
        """
        return (a - b + pi) % (2*pi) - pi

    def __init__(self, direction, angle):
        self.direction = direction
        self._empty = degrees(angle) < self.empty_angle
        self.half_angle = angle /2.0
        self.start = self.normalize(
            self.direction - self.half_angle
        )
        self.end = self.normalize(
            self.direction + self.half_angle
        )
    def contains(self, angle):
        """
        Works even if sector crosses 0°
        """
        if self.empty:
            return False

        delta = abs(
            self.angle_diff(angle, self.direction)
        )

        return delta <= self.half_angle
    
    def __iadd__(self, other):
        """
        Intersection of sectors.
        """

        if self.empty or other.empty:
            self.empty = True
            return self

        # Express other sector in self's local coordinates.
        delta = self.angle_diff(
            other.direction,
            self.direction
        )

        a0 = -self.half_angle
        a1 = self.half_angle

        b0 = delta - other.half_angle
        b1 = delta + other.half_angle

        start = max(a0, b0)
        end = min(a1, b1)

        if end <= start:
            self.empty = True
            return self

        self.half_angle = (end - start) / 2.0

        center_local = (start + end) / 2.0

        self.direction = self.normalize(
            self.direction + center_local
        )

        self.start = self.normalize(
            self.direction - self.half_angle
        )

        self.end = self.normalize(
            self.direction + self.half_angle
        )

        if degrees(2 * self.half_angle) < self.empty_angle:
            self.empty = True

        return self
    
    @property
    def empty(self):
        return self._empty
    
    @empty.setter
    def empty(self, value):
        self._empty = value
        if value:
            self.start = None
            self.end = None
            self.direction = None
            self.half_angle = None
