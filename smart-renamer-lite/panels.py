import bpy

class SMART_RENAMER_PT_main_panel(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport Sidebar"""
    bl_label = "Smart Renamer Lite"
    bl_idname = "SMART_RENAMER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Smart Renamer Lite"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        # Access Addon Preferences
        addon_prefs = context.preferences.addons.get(__package__).preferences
        
        if not addon_prefs.api_key:
            box = layout.box()
            box.label(text="Setup Required", icon='ERROR')
            row = box.row()
            row.operator("preferences.addon_show", text="Open Preferences", icon='PREFERENCES').module = __package__
            layout.separator()
        
        # Configuration Box
        box = layout.box()
        box.label(text="Configuration", icon='PREFERENCES')
        
        box.separator()
        box.prop(scene, "smart_renamer_context", text="Context", icon='INFO')
        
        box.prop(scene, "smart_renamer_naming_style", text="Style")
        box.prop(scene, "smart_renamer_view_mode", text="Views")
        
        box.prop(scene, "smart_renamer_include_context", text="Include Context View")
        
        layout.separator()

        # Action Section
        col = layout.column()
        col.scale_y = 1.6
        
        if scene.smart_renamer_is_processing:
            col.label(text=scene.smart_renamer_status, icon='TIME')
        else:
            col.operator("smart_renamer.analyze_rename", icon='GREASEPENCIL')
        
        if not addon_prefs.api_key:
            col.enabled = False
