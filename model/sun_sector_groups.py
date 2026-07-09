from util import hour_to_string

class SunSectorGroups(list):
    def __init__(self, insolation_scale):
        self.insolation_scale = insolation_scale
        sectors = insolation_scale.sectors

        if not sectors: return
        
        current = SunSectorGroup(self, sectors[0])    
        self.append(current)

        for sector in sectors[1:]:
            if sector.shadow == current.shadow:
                current.append(sector)
                continue
            current = SunSectorGroup(self, sector)
            self.append(current)

        # Suppress short Sun groups
        sun_groups = [group for group in self if not group.shadow]

        if len(sun_groups) > 2:
            sun_groups.sort(key=lambda group: group.duration, reverse=True)

            for group in sun_groups[2:]:
                    group.state = 'Suppressed'

    @property
    def range(self):
        total, range = 0, ''
        ranges = list()
        for group in self:
            if group.state != 'Sun': continue
            t, r = group.range
            total += t
            ranges.append(r)
        if total:
            range = '%s [%s]' % ('; '.join(ranges), hour_to_string(total))

        return total, range
    



class SunSectorGroup(list):
    shadow_states = {
        True: 'Shadow',
        False: 'Sun',
    }

    def __init__(self, insolation_scale, sector):
        self.insolation_scale = insolation_scale

        self.shadow = sector.shadow
        self.state = self.shadow_states[sector.shadow]
        self.append(sector)

    @property
    def range(self):
        rise, down = self[0], self[-1]
        rise, down = rise.start.hour, down.end.hour
        total = down - rise
        range = '%s÷%s' % (hour_to_string(rise), hour_to_string(down))
        return total, range
    
    @property
    def duration(self):
        return self[-1].end.hour - self[0].start.hour    
