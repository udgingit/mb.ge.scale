from numpy import array
from scipy.spatial import Delaunay  # type: ignore

from .protection_point import ProtectionPoint
from .protection_simplice import (
    SimpliceByOneProtectionPoint,
    SimpliceByThreeProtectionPoints
    )


class ProtectionSurface(object):
    def __init__(self, holders, plane, radius):
        self.plane = plane
        self.plane_elevation = plane.Origin.Z
        self.radius = radius
        
        self.points = [
            ProtectionPoint(self, holder, index)
            for index, holder in enumerate(holders)
        ]
        #TODO ohne dieses Quatsch
        self.already_protected = [point.errors for point in self.points if point.is_protected()]
        self.points = [point for point in self.points if not point.is_protected()]
        self.points = [ProtectionPoint(self, point.holder, index) for index, point in enumerate(self.points)]

        tri = Delaunay(array(
            [point.xy for point in self.points]
        ))

        self.simplices = [
            SimpliceByThreeProtectionPoints(
                self,
                [self.points[index] for index in simplice]
            ) for simplice in tri.simplices
        ]

        [simplice.build_edges() for simplice in self.simplices if simplice.is_valid]

        self.perimeter = set()
        for simplice in self.simplices:
            if type(simplice).__name__ == 'SimpliceByTwoProtectionPoints':
                if simplice.is_valid:
                    self.perimeter.update(simplice.indices)
                    

        self.perimeter = {
            index for simplice in self.simplices
            #I don't know how to make
            #if type(simplice) is SimpliceByTwoProtectionPoints
            if type(simplice).__name__ == 'SimpliceByTwoProtectionPoints' and
                simplice.is_valid
            for index in simplice.indices
        }
        

        self.simplices.extend([SimpliceByOneProtectionPoint(self, self.points[index]) for index in self.perimeter])
                