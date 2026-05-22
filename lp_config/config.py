import os
import json

from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import (
    FilteredElementCollector, ParameterValueProvider, Transaction,
    ParameterElement, BuiltInCategory, Material,
    GraphicsStyleType, Color,
)


class Config(object):
    file_name = 'config.json'
    error_title = 'Error:('
    properties = [
        'values'
    ]
    key_project_parameters = 'project_parameters'
    key_line_styles = 'line_styles'
    key_materials = 'materials'

    def __init__(self, doc, project_dir):
        self.succeed = False
        self.doc = doc
        self.project_dir = project_dir

        try:
            full_path = os.path.join(self.project_dir, self.file_name)
            with open(full_path, 'r', encoding='utf-8') as file:
                self.data = json.load(file)
                self.suceed = True
        except IOError:
            TaskDialog.Show(self.error_title, 'Cannot find config file %s' % full_path)
        except json.JSONDecodeError:
            TaskDialog.Show(self.error_title, 'Error: The file is not valid JSON')

        for property in self.properties:
            if property in self.data:
                values = self.data[property]
                setattr(self, property, DataGroup(values))

    def find_project_parameters(self):
        if self.key_project_parameters in self.data:
            data = self.data[self.key_project_parameters]
            flipped = {value: key for key, value in data.items()}
            names = data.values()

            parameters = FilteredElementCollector(self.doc).OfClass(ParameterElement).ToElements()
            try:
                parameters.sort(key=lambda x: x.Id.IntegerValue)
            except:
                parameters.sort(key=lambda x: x.Id.Value)

            project_parameters = dict()
            for parameter in parameters:
                definition = parameter.GetDefinition()
                name = definition.Name
                if name in names:
                    project_parameters[flipped[name]] = ProjectParameterData(name, parameter, definition)
            self.project_parameters = DataGroup(project_parameters)

            missing = [key for key in data if key not in project_parameters]
            missing = [data[key] for key in missing]
            if missing:
                TaskDialog.Show(
                    self.error_title,
                    f'The following ProjectParameters are missing in the project:\n%s ' % f'\n'.join(missing)
                )
        
    #TODO create dict with foo for every data key
    #TODO check if object was created
    def found_line_styles(self):
        if self.key_line_styles in self.data:
            data = self.data[self.key_line_styles]
            flipped = {value: key for key, value in data.items()}
            names = data.values()
            
            categories = self.doc.Settings.Categories
            subcategories = categories.get_Item(BuiltInCategory.OST_Lines).SubCategories
            styles = {flipped[sub.Name]: LineStyleData(sub.Name, sub) for sub in subcategories if sub.Name in names}
                    
            self.line_styles = DataGroup(styles)
            missing = [key for key in data if key not in styles]
            missing = [data[key] for key in missing]
            if missing: TaskDialog.Show(
                self.error_title,
                'Line style(s) not found:(\n%s ' % ',\n'.join(missing)
            )
            #TODO show also key name
            #TODO think about TaskDialog message

    def find_materials(self):
        if self.key_materials in self.data:
            materials = FilteredElementCollector(self.doc).OfClass(Material).ToElements()
            material_map = {
                material.Name: material for material in materials
            }
            data = self.data[self.key_materials] 
            names = [current['name'] for current in data.values()]
            
            flipped = {data[current]['name']: current for current in data}

            transaction = Transaction(self.doc)
            transaction.Start('Adjust Materials')
            try:
                materials = dict()
                for name in names:
                    if name in material_map:
                        material = material_map[name]
                        material_id = material.Id
                    else:
                        material_id = None

                    materials[flipped[name]] = MaterialData(
                        self.doc, name,
                        material_id,
                        data[flipped[name]]
                    )
                transaction.Commit()                    
            except Exception as e:
                transaction.RollBack()
                TaskDialog.Show('Material error;(', 'Error during material adjusting')

            self.materials = DataGroup(materials)


class DataGroup(object):
    def __init__(self, values):
        for key, value in values.items():
            setattr(self, key, value)


class ProjectParameterData(object):
    def __init__(self, name, parameter, definition):
        self.name = name
        self.parameter = parameter
        self.id = parameter.Id
        self.provider = ParameterValueProvider(self.id)
        self.definition = definition
        #TODO check Parameters<=>Categories


class LineStyleData(object):
    def __init__(self, name, subcategorie):
        self.name = name
        self.subcategorie = subcategorie
        self.graphic_style = subcategorie.GetGraphicsStyle(GraphicsStyleType.Projection)


class MaterialData(object):
    default = {
        'color': (255, 127, 39),
        'transparency': 15,
        'shininess': 1,
        'smoothness': 1
    }
    def __init__(self, doc, name, material_id, data):
        self.name = name
        self.material_id = material_id
        for key in self.default:
            if key in data:
                value = data[key]
            else:
                value = self.default[key]
            setattr(self, key, value)

        self.material_id = self.adjust_or_create(
            doc,
            material_id = self.material_id,
            name=self.name,
            color=self.color,
            transparency=self.transparency,
            shininess=self.shininess,
            smoothness=self.smoothness
        )

    @classmethod
    def adjust_or_create(cls, doc, material_id=None, name='New Material', color=(255, 127, 39), transparency=15, shininess=0.5, smoothness=0.5):
        """
        Creates a new Revit material with basic properties.
        
        Parameters:
            doc (Document): The active Revit document.
            name (str): The name of the new material.
            color (tuple): RGB tuple, e.g. (255, 0, 0) for red.
            transparency (int): 0-100, 0 = opaque.
            shininess (float): Specular reflection (0-1).
            smoothness (float): Glossiness (0-1).
        
        Returns:
            Material Id: The Id of created Material object.
        """
        if material_id is None:
            material_id = Material.Create(doc, name)
        material = doc.GetElement(material_id)        
            
        material.Color = Color(color[0], color[1], color[2])
        material.Transparency = transparency
        material.Shininess = shininess
        material.Smoothness = smoothness
        return material.Id        
