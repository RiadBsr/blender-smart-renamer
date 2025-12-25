import bpy

class SMART_RENAMER_PT_main_panel(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport Sidebar"""
    bl_label = "Smart Renamer"
    bl_idname = "SMART_RENAMER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Smart Renamer"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Access Addon Preferences
        addon_prefs = context.preferences.addons.get(__package__).preferences
        
        if not addon_prefs.api_key:
            layout.label(text="API Key missing!", icon='ERROR')
            layout.operator("preferences.addon_show", text="Open Preferences").module = __package__
            layout.separator()
        
        # Settings Section
        layout.label(text="Settings:")
        layout.prop(scene, "smart_renamer_naming_style")
        
        layout.label(text="Target:")
        row = layout.row()
        row.prop(scene, "smart_renamer_scope", expand=True)

        layout.separator()

        # Action Section
        row = layout.row()
        row.scale_y = 1.5
        row.operator("smart_renamer.analyze_rename", icon='SHADING_RENDERED')
        
        if not addon_prefs.api_key:
            row.enabled = False
