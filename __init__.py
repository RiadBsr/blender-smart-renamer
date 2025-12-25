import bpy
from .operators import SMART_RENAMER_OT_analyze_rename
from .panels import SMART_RENAMER_PT_main_panel

bl_info = {
    "name": "Smart Renamer AI",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Smart AI",
    "description": "Renames objects using Gemini Vision AI",
    "category": "Object",
}

class SmartRenamerPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    api_key: bpy.props.StringProperty(
        name="API Key",
        description="Google Gemini API Key",
        default="",
        subtype='PASSWORD'
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "api_key")
        layout.label(text="Get your API key from Google AI Studio")

def register():
    try:
        bpy.utils.register_class(SmartRenamerPreferences)
        bpy.utils.register_class(SMART_RENAMER_OT_analyze_rename)
        bpy.utils.register_class(SMART_RENAMER_PT_main_panel)
    except ValueError:
        pass # Already registered
    
    # Register Scene Properties
    # API Key moved to Preferences
    
    bpy.types.Scene.smart_renamer_naming_style = bpy.props.EnumProperty(
        name="Naming Style",
        description="Select the naming convention",
        items=[
            ('Snake_Case', "Snake_Case", "e.g. sci_fi_crate"),
            ('CamelCase', "CamelCase", "e.g. SciFiCrate"),
            ('Unreal_Prefix', "Unreal_Prefix", "e.g. SM_Crate"),
            ('Descriptive', "Descriptive", "Natural language description"),
        ],
        default='Snake_Case'
    )
    
    bpy.types.Scene.smart_renamer_scope = bpy.props.EnumProperty(
        name="Scope",
        description="Rename Active Object or All Selected",
        items=[
            ('ACTIVE', "Rename Active", "Only rename the active object"),
            ('SELECTED', "Rename Selected", "Rename all selected objects"),
        ],
        default='ACTIVE'
    )

def unregister():
    if hasattr(bpy.types.Scene, "smart_renamer_api_key"):
        del bpy.types.Scene.smart_renamer_api_key
    if hasattr(bpy.types.Scene, "smart_renamer_naming_style"):
        del bpy.types.Scene.smart_renamer_naming_style
    if hasattr(bpy.types.Scene, "smart_renamer_scope"):
        del bpy.types.Scene.smart_renamer_scope
    
    bpy.utils.unregister_class(SMART_RENAMER_PT_main_panel)
    bpy.utils.unregister_class(SMART_RENAMER_OT_analyze_rename)
    bpy.utils.unregister_class(SmartRenamerPreferences)


if __name__ == "__main__":
    register()