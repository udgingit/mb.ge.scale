from util import detect_intersection

class SunSectors(list):
    def __init__(self, insolation_scale):
        self.insolation_scale = insolation_scale
        self.exceptions = set((insolation_scale.holder.Id, insolation_scale.host.Id))
        for start, end in zip(insolation_scale.rays, insolation_scale.rays[1:]):
            self.append(SunSector(self, start, end))  


class SunSector(object):
    def __init__(self, sun_sectors, start, end):
        self.start = start
        self.end = end
        intersector = sun_sectors.insolation_scale.intersector
        origin = sun_sectors.insolation_scale.origin
        exceptions = sun_sectors.exceptions

        start_state = detect_intersection(intersector, origin, start.sun, exceptions)
        end_state = detect_intersection(intersector, origin, end.sun, exceptions)

        self.shadow = start_state or end_state  # true = in shadow
