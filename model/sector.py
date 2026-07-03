from math import pi, degrees
from util import xyz_to_direction


class Sector(object):
    empty_angle = 0.5

    def __init__(self, vector, half_angle):
        self.vector = vector
        self.empty = degrees(half_angle) < self.empty_angle
        self.angle = half_angle*2
        self.start = vector.rotated(-half_angle)
        self.end = vector.rotated(half_angle)
    
    @property
    def limits(self):
        return (self.start, self.end)
    
    def contains(self, vector):
        return vector.inside(self.limits)    
