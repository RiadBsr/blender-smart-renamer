import bpy
from .operators import SMART_RENAMER_OT_analyze_rename, SMART_RENAMER_OT_cancel_process
from .panels import SMART_RENAMER_PT_main_panel

bl_info = {
    "name": "Smart Renamer",
    "author": "Riad Boussoura",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Smart Renamer",
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
    ) # type: ignore

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "api_key")
        layout.label(text="Get your API key from Google AI Studio")

def register():
    try:
        bpy.utils.register_class(SmartRenamerPreferences)
        bpy.utils.register_class(SMART_RENAMER_OT_analyze_rename)
        bpy.utils.register_class(SMART_RENAMER_OT_cancel_process)
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
            ('CamelCase', "PascalCase (Camel)", "e.g. SciFiCrate"),
            ('lowerCamelCase', "lowerCamelCase", "e.g. sciFiCrate"),
            ('UPPER_SNAKE_CASE', "UPPER_SNAKE_CASE", "e.g. SCI_FI_CRATE"),
            ('Kebab-Case', "Kebab-Case", "e.g. sci-fi-crate"),
            ('Unreal_Prefix', "Unreal_Prefix", "e.g. SM_Crate"),
            ('Descriptive', "Descriptive", "Natural language description"),
        ],
        default='Snake_Case'
    )
    
    bpy.types.Scene.smart_renamer_context = bpy.props.StringProperty(
        name="Context",
        description="Additional context for the AI (e.g., 'Sci-fi game assets', 'Low poly style')",
        default=""
    )
    
    bpy.types.Scene.smart_renamer_view_mode = bpy.props.EnumProperty(
        name="Isolated Views",
        description="Choose which isolated views to capture",
        items=[
            ('FRONT', "Front Only", "Faster, less detail"),
            ('FRONT_BACK', "Front & Back", "Slower, better accuracy"),
        ],
        default='FRONT_BACK'
    )
    
    bpy.types.Scene.smart_renamer_include_context = bpy.props.BoolProperty(
        name="Include Context",
        description="Include a screenshot of the object in the scene context (Slower, but helps with scale/location)",
        default=False
    )

    bpy.types.Scene.smart_renamer_status = bpy.props.StringProperty(
        name="Status",
        description="Current status of the renaming process",
        default="Ready"
    )

    bpy.types.Scene.smart_renamer_is_processing = bpy.props.BoolProperty(
        name="Is Processing",
        description="Whether the addon is currently processing",
        default=False
    )

    bpy.types.Scene.smart_renamer_fast_mode = bpy.props.BoolProperty(
        name="Fast Mode",
        description="Use smaller, faster models (4b) instead of high-quality ones (27b). Good for simple objects.",
        default=False
    )

def unregister():
    if hasattr(bpy.types.Scene, "smart_renamer_api_key"):
        del bpy.types.Scene.smart_renamer_api_key
    if hasattr(bpy.types.Scene, "smart_renamer_naming_style"):
        del bpy.types.Scene.smart_renamer_naming_style
    if hasattr(bpy.types.Scene, "smart_renamer_context"):
        del bpy.types.Scene.smart_renamer_context
    if hasattr(bpy.types.Scene, "smart_renamer_view_mode"):
        del bpy.types.Scene.smart_renamer_view_mode
    if hasattr(bpy.types.Scene, "smart_renamer_include_context"):
        del bpy.types.Scene.smart_renamer_include_context
    if hasattr(bpy.types.Scene, "smart_renamer_status"):
        del bpy.types.Scene.smart_renamer_status
    if hasattr(bpy.types.Scene, "smart_renamer_is_processing"):
        del bpy.types.Scene.smart_renamer_is_processing
    if hasattr(bpy.types.Scene, "smart_renamer_fast_mode"):
        del bpy.types.Scene.smart_renamer_fast_mode
    
    bpy.utils.unregister_class(SMART_RENAMER_PT_main_panel)
    bpy.utils.unregister_class(SMART_RENAMER_OT_analyze_rename)
    bpy.utils.unregister_class(SMART_RENAMER_OT_cancel_process)
    bpy.utils.unregister_class(SmartRenamerPreferences)


if __name__ == "__main__":
    register()