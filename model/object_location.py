from math import degrees, sin, cos
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInParameter, BuiltInCategory,
    XYZ,
)


class ObjectLocation(object):
    def __init__(self, doc):
        self.doc = doc
        self.location = self.doc.ActiveProjectLocation
        self.site = self.location.GetSiteLocation()
        
        self.latitude = self.site.Latitude      # radians
        self.longitude = self.site.Longitude    # radians

        base_point = FilteredElementCollector(doc) \
            .OfCategory(BuiltInCategory.OST_ProjectBasePoint) \
            .FirstElement()

        self.north_angle = base_point.get_Parameter(BuiltInParameter.BASEPOINT_ANGLETON_PARAM).AsDouble()
        self.north = XYZ(
            sin(self.north_angle),
            cos(self.north_angle),
            0
        )
    
    @property
    def latitude_deg(self):
        return degrees(self.latitude)
    
    @property
    def longitude_deg(self):
        return degrees(self.longitude)
    
    @property
    def north_angle_deg(self):
        return degrees(self.north_angle)
    
    def show(self):
        TaskDialog.Show(
            'Project Location',
            'Latitude: %f°; Longitude: %f°\nNorth direction: %f' % (
                self.latitude_deg,
                self.longitude_deg,
                self.north_angle_deg
            )
        )
