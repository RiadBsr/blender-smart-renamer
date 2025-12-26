import bpy
import os
import tempfile
import base64
import math
import mathutils

def get_temp_image_path():
    temp_dir = tempfile.gettempdir()
    return os.path.join(temp_dir, "smart_renamer_temp.png")

def take_isolated_screenshot(obj, context):
    """
    Isolates the object, creates a temp camera, renders a 512x512 thumbnail, 
    and returns the file path. Does not affect user viewport.
    """
    scene = context.scene
    view_layer = context.view_layer
    
    # 1. Store current state
    original_res_x = scene.render.resolution_x
    original_res_y = scene.render.resolution_y
    original_res_pct = scene.render.resolution_percentage
    original_camera = scene.camera
    original_filepath = scene.render.filepath
    
    original_selection = context.selected_objects
    original_active = context.active_object
    
    # Store visibility state of all objects in the view layer
    visibility_map = {}
    for o in view_layer.objects:
        visibility_map[o] = o.hide_get()
    
    temp_cam_obj = None
    
    try:
        # 2. Set Resolution (512x512) for speed and consistency
        scene.render.resolution_x = 512
        scene.render.resolution_y = 512
        scene.render.resolution_percentage = 100
        
        # 3. Isolate Object
        bpy.ops.object.select_all(action='DESELECT')
        
        # Ensure the object is selectable and visible
        obj.hide_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        # Hide everything else
        for o in view_layer.objects:
            if o != obj:
                o.hide_set(True)
                
        # 4. Setup Temp Camera
        # Create camera data and object
        cam_data = bpy.data.cameras.new(name='SmartRenamer_TempCam')
        temp_cam_obj = bpy.data.objects.new('SmartRenamer_TempCam', cam_data)
        scene.collection.objects.link(temp_cam_obj)
        scene.camera = temp_cam_obj
        
        # Calculate framing (Math-based, no viewport operators)
        # Get bounding box in world space
        bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
        center = sum(bbox_corners, mathutils.Vector()) / 8
        
        # Get radius (max distance from center to corner)
        radius = max((corner - center).length for corner in bbox_corners)
        if radius == 0: radius = 1.0 # Fallback for empty/point objects
        
        # Position camera: Front-Right-Top angle
        direction = mathutils.Vector((1.0, -1.2, 0.8)).normalized()
        
        # Distance to fit object in FOV
        # Default camera angle is ~39.6 degrees (horizontal)
        fov = cam_data.angle
        distance = (radius * 2.0) / math.sin(fov / 2) # 2.0 safety factor for padding
        
        camera_pos = center + direction * distance
        temp_cam_obj.location = camera_pos
        
        # Point camera at center
        direction_to_center = center - camera_pos
        rot_quat = direction_to_center.to_track_quat('-Z', 'Y')
        temp_cam_obj.rotation_euler = rot_quat.to_euler()
        
        # 5. Render
        filepath = get_temp_image_path()
        scene.render.filepath = filepath
        scene.render.image_settings.file_format = 'PNG'
        
        # Render OpenGL using the active camera (view_context=False)
        # This renders what the camera sees, not the viewport
        bpy.ops.render.opengl(write_still=True, view_context=False)
        
        return filepath

    finally:
        # 6. Restore State
        scene.render.resolution_x = original_res_x
        scene.render.resolution_y = original_res_y
        scene.render.resolution_percentage = original_res_pct
        scene.render.filepath = original_filepath
        scene.camera = original_camera
        
        # Cleanup temp camera
        if temp_cam_obj:
            bpy.data.objects.remove(temp_cam_obj, do_unlink=True)
            # Also remove the camera data block
            if cam_data:
                bpy.data.cameras.remove(cam_data, do_unlink=True)
        
        # Restore visibility
        for o, hidden in visibility_map.items():
            try:
                o.hide_set(hidden)
            except ReferenceError:
                pass 
        
        # Restore selection
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
