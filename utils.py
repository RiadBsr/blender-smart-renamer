import bpy
import os
import tempfile
import base64

def get_temp_image_path():
    temp_dir = tempfile.gettempdir()
    return os.path.join(temp_dir, "smart_renamer_temp.png")

def take_isolated_screenshot(obj, context):
    """
    Isolates the object, takes a viewport render, and returns the file path.
    """
    scene = context.scene
    view_layer = context.view_layer
    
    # 1. Store current state
    original_selection = context.selected_objects
    original_active = context.active_object
    
    # Store visibility state of all objects in the view layer
    visibility_map = {}
    for o in view_layer.objects:
        visibility_map[o] = o.hide_get()
    
    try:
        # 2. Isolate Object
        bpy.ops.object.select_all(action='DESELECT')
        
        # Ensure the object is selectable and visible
        obj.hide_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        # Hide everything else
        for o in view_layer.objects:
            if o != obj:
                o.hide_set(True)
                
        # 3. Frame the object
        # We need a 3D view context for view_selected
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        override = {
                            'window': context.window,
                            'screen': context.screen,
                            'area': area,
                            'region': region,
                            'scene': scene,
                        }
                        with context.temp_override(**override):
                            bpy.ops.view3d.view_selected()
                            # Optional: Zoom out slightly or adjust view?
                            pass
                        break
        
        # 4. Render
        filepath = get_temp_image_path()
        
        # Set render settings for speed
        original_render_filepath = scene.render.filepath
        scene.render.filepath = filepath
        scene.render.image_settings.file_format = 'PNG'
        
        # Render OpenGL (Viewport)
        # We need to override context for render.opengl if we are not in a 3D view, 
        # but usually the operator is called from 3D view.
        # If called from a button in N-Panel, context is usually fine.
        bpy.ops.render.opengl(write_still=True, view_context=True)
        
        # Restore render filepath
        scene.render.filepath = original_render_filepath
        
        return filepath

    finally:
        # 5. Restore State
        for o, hidden in visibility_map.items():
            try:
                o.hide_set(hidden)
            except ReferenceError:
                pass # Object might have been deleted? Unlikely here.
        
        bpy.ops.object.select_all(action='DESELECT')
        for o in original_selection:
            try:
                o.select_set(True)
            except ReferenceError:
                pass
                
        if original_active:
            try:
                view_layer.objects.active = original_active
            except ReferenceError:
                pass

def image_to_base64(filepath):
    """
    Reads an image file and converts it to a base64 string.
    """
    if not os.path.exists(filepath):
        return None
        
    with open(filepath, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    return encoded_string
