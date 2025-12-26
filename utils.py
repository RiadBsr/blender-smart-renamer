import bpy
import os
import tempfile
import base64
import math
import mathutils

def get_temp_image_path(suffix=""):
    temp_dir = tempfile.gettempdir()
    return os.path.join(temp_dir, f"smart_renamer_temp{suffix}.png")

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
        # Reduced safety factor from 2.0 to 1.1 for tighter zoom (minimum void margins)
        distance = (radius * 1.1) / math.sin(fov / 2) 
        
        camera_pos = center + direction * distance
        temp_cam_obj.location = camera_pos
        
        # Adjust clipping to ensure large objects are visible
        # Distance to center + radius covers the back of the object. 
        # We add some margin.
        required_clip_end = distance + radius * 2.0
        # Default clip_end is often 100m or 1000m. If object is huge, we need more.
        if cam_data.clip_end < required_clip_end:
            cam_data.clip_end = required_clip_end

        # Point camera at center
        direction_to_center = center - camera_pos
        rot_quat = direction_to_center.to_track_quat('-Z', 'Y')
        temp_cam_obj.rotation_euler = rot_quat.to_euler()
        
        # 5. Render
        filepath = get_temp_image_path("_iso")
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

def take_context_screenshot(obj, context):
    """
    Takes a screenshot of the object within the scene (no isolation),
    highlighted (selected), using Viewport Shading (X-Ray/Wireframe).
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
    
    # Store object display state
    original_show_in_front = obj.show_in_front
    original_show_wire = obj.show_wire
    
    # Find 3D View Area
    area = None
    space = None
    region = None
    for a in context.screen.areas:
        if a.type == 'VIEW_3D':
            area = a
            space = a.spaces.active
            for r in a.regions:
                if r.type == 'WINDOW':
                    region = r
            break
            
    if not space:
        return None # Cannot take context screenshot without a 3D view

    # Store Viewport State
    original_shading_type = space.shading.type
    original_xray = space.shading.show_xray
    original_viewport_camera = space.camera
    original_perspective = space.region_3d.view_perspective
    original_overlays = space.overlay.show_overlays
    
    # Store View Transform (Location, Rotation, Distance)
    original_view_location = space.region_3d.view_location.copy()
    original_view_rotation = space.region_3d.view_rotation.copy()
    original_view_distance = space.region_3d.view_distance
    original_view_camera_zoom = space.region_3d.view_camera_zoom
    original_view_camera_offset = tuple(space.region_3d.view_camera_offset)
    
    temp_cam_obj = None
    
    try:
        # 2. Set Resolution (512x512)
        scene.render.resolution_x = 512
        scene.render.resolution_y = 512
        scene.render.resolution_percentage = 100
        
        # 3. Select Object (Ensure it is highlighted)
        bpy.ops.object.select_all(action='DESELECT')
        obj.hide_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        # 4. Setup Temp Camera
        cam_data = bpy.data.cameras.new(name='SmartRenamer_ContextCam')
        temp_cam_obj = bpy.data.objects.new('SmartRenamer_ContextCam', cam_data)
        scene.collection.objects.link(temp_cam_obj)
        scene.camera = temp_cam_obj
        
        # Calculate framing
        bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
        center = sum(bbox_corners, mathutils.Vector()) / 8
        radius = max((corner - center).length for corner in bbox_corners)
        if radius == 0: radius = 1.0
        
        direction = mathutils.Vector((1.0, -1.2, 0.8)).normalized()
        fov = cam_data.angle
        
        # Use larger distance factor for context (e.g., 2.5x)
        distance = (radius * 2.5) / math.sin(fov / 2) 
        
        camera_pos = center + direction * distance
        temp_cam_obj.location = camera_pos
        
        required_clip_end = distance + radius * 4.0 # More depth for context
        if cam_data.clip_end < required_clip_end:
            cam_data.clip_end = required_clip_end

        direction_to_center = center - camera_pos
        rot_quat = direction_to_center.to_track_quat('-Z', 'Y')
        temp_cam_obj.rotation_euler = rot_quat.to_euler()
        
        # 5. Configure Viewport for Render
        space.camera = temp_cam_obj
        space.region_3d.view_perspective = 'CAMERA'
        space.shading.type = 'SOLID'
        space.shading.show_xray = True
        space.overlay.show_overlays = True
        obj.show_wire = True
        
        # 6. Render
        filepath = get_temp_image_path("_ctx")
        scene.render.filepath = filepath
        scene.render.image_settings.file_format = 'PNG'
        
        # Context Override for Viewport Render
        override = context.copy()
        override['area'] = area
        override['region'] = region
        override['space_data'] = space
        override['scene'] = scene
        override['screen'] = context.screen
        
        if hasattr(context, "temp_override"):
            with context.temp_override(area=area, region=region):
                bpy.ops.render.opengl(write_still=True, view_context=True)
        else:
            bpy.ops.render.opengl(override, write_still=True, view_context=True)
        
        return filepath

    finally:
        # 7. Restore State
        scene.render.resolution_x = original_res_x
        scene.render.resolution_y = original_res_y
        scene.render.resolution_percentage = original_res_pct
        scene.render.filepath = original_filepath
        scene.camera = original_camera
        
        # Restore Viewport State
        if space:
            space.shading.type = original_shading_type
            space.shading.show_xray = original_xray
            space.camera = original_viewport_camera
            space.region_3d.view_perspective = original_perspective
            space.overlay.show_overlays = original_overlays
            
            # Restore View Transform
            space.region_3d.view_location = original_view_location
            space.region_3d.view_rotation = original_view_rotation
            space.region_3d.view_distance = original_view_distance
            space.region_3d.view_camera_zoom = original_view_camera_zoom
            space.region_3d.view_camera_offset = original_view_camera_offset
        
        # Restore object display state
        try:
            obj.show_in_front = original_show_in_front
            obj.show_wire = original_show_wire
        except ReferenceError:
            pass
        
        if temp_cam_obj:
            bpy.data.objects.remove(temp_cam_obj, do_unlink=True)
            if cam_data:
                bpy.data.cameras.remove(cam_data, do_unlink=True)
        
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
