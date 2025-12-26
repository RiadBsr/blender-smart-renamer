import bpy
import threading
import queue
import json
import urllib.request
import urllib.error
import time
from . import utils

# Global queues
# result_queue: passes results from worker thread to main thread (Blender)
result_queue = queue.Queue()
# task_queue: holds pending API requests to be processed sequentially
task_queue = queue.Queue()

# Gemma 3 Family - High Throughput Chain
# Each has ~30 RPM. Chaining them gives theoretical ~150 RPM.
GEMMA_MODELS = [
    "gemma-3-27b-it",
    "gemma-3-12b-it",
    "gemma-3-4b-it",
    "gemma-3-2b-it",
    "gemma-3-1b-it"
]

NAMING_STYLE_DESCRIPTIONS = {
    'Snake_Case': "lowercase words separated by underscores (e.g., `sci_fi_crate`).",
    'CamelCase': "Capitalized words concatenated without spaces (e.g., `SciFiCrate`).",
    'Unreal_Prefix': "Asset type prefix followed by PascalCase (e.g., `SM_Crate` for static meshes).",
    'Descriptive': "A short, natural language description (e.g., `Old Wooden Crate`)."
}

def send_gemini_request(api_key, images_b64, naming_style, obj_name, model_name, context_text="", collection_name="", dimensions="", recent_names=None):
    """
    Sends request to specific model. Returns dict with result or error code.
    """
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key.strip()}"
        
        headers = {'Content-Type': 'application/json'}
        
        style_desc = NAMING_STYLE_DESCRIPTIONS.get(naming_style, naming_style)
        
        # Updated prompt with richer context and expert persona
        prompt_text = (
            f"You are an expert 3D Technical Artist specializing in asset management. "
            f"Your task is to analyze these viewport renders and generate a precise, descriptive name for the 3D object.\n"
            f"The images provided may include: Isolated Front View, Isolated Back View, and a Context View (highlighted in scene).\n\n"
            f"Object Metadata:\n"
            f"- Current Name: \"{obj_name}\" (might be generic/incorrect)\n"
            f"- Collection: \"{collection_name}\"\n"
            f"- Dimensions: {dimensions}\n\n"
            f"Naming Rules:\n"
            f"1. Style: {naming_style} ({style_desc})\n"
            f"2. Be descriptive but concise. Avoid generic names like 'Cube' or 'Mesh'.\n"
            f"3. Return ONLY a JSON object: {{\"name\": \"new_name\"}}.\n"
        )
        
        if context_text:
            prompt_text += f"4. Project Context: {context_text}\n"
            
        if recent_names:
            prompt_text += (
                f"5. Batch Context: Recently named objects: {', '.join(recent_names[-10:])}. "
                f"Use this ONLY to maintain naming consistency for identical objects. "
                f"CRITICAL: Do not copy previous names if the object is different. "
                f"Be specific (e.g., name a 'piston' as 'piston', not 'engine_block').\n"
            )
        
        parts = [{"text": prompt_text}]
        for img_b64 in images_b64:
            if img_b64:
                parts.append({
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": img_b64
                    }
                })

        data = {
            "contents": [{
                "parts": parts
            }]
        }
        
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if 'candidates' not in result or not result['candidates']:
                 return {'obj_name': obj_name, 'error': "API returned no candidates. Safety filter?"}

            text_response = result['candidates'][0]['content']['parts'][0]['text']
            
            # Robust Parsing Logic
            try:
                # 1. Clean Markdown
                clean_text = text_response.replace('```json', '').replace('```', '').strip()
                
                # 2. Find JSON boundaries
                start_idx = clean_text.find('{')
                end_idx = clean_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    clean_text = clean_text[start_idx:end_idx+1]
                
                new_name_data = json.loads(clean_text)
                return {'obj_name': obj_name, 'new_name': new_name_data.get('name', obj_name)}
                
            except json.JSONDecodeError:
                # Fallback for single quotes or malformed JSON
                import ast
                try:
                    new_name_data = ast.literal_eval(clean_text)
                    return {'obj_name': obj_name, 'new_name': new_name_data.get('name', obj_name)}
                except:
                    return {'obj_name': obj_name, 'error': f"JSON Parse Error: {clean_text[:50]}..."}

    except urllib.error.HTTPError as e:
        if e.code == 429:
            return {'obj_name': obj_name, 'status_code': 429} # Special signal for rate limit
        return {'obj_name': obj_name, 'error': f"API Error {e.code}: {e.reason}"}
    except ValueError as e:
        return {'obj_name': obj_name, 'error': f"Invalid API Key or URL: {str(e)}"}
    except Exception as e:
        return {'obj_name': obj_name, 'error': str(e)}

def batch_worker(api_key, naming_style):
    print("Smart Renamer: Batch worker started.")
    
    # Start with the best model
    current_model_index = 0
    recent_names = []
    
    while not task_queue.empty():
        item = task_queue.get()
        obj_name = item['obj_name']
        images_b64 = item['images_b64']
        context_text = item.get('context', "")
        collection_name = item.get('collection_name', "")
        dimensions = item.get('dimensions', "")
        
        # Try to process
        success = False
        retry_count = 0
        
        while not success and retry_count < len(GEMMA_MODELS) + 1:
            current_model = GEMMA_MODELS[current_model_index]
            print(f"Smart Renamer: Processing '{obj_name}' using {current_model}...")
            
            result = send_gemini_request(
                api_key, images_b64, naming_style, obj_name, current_model, 
                context_text, collection_name, dimensions, recent_names
            )
            
            if result.get('status_code') == 429:
                print(f"Smart Renamer: Rate limit hit on {current_model}. Downgrading...")
                
                # Move to next model in chain
                current_model_index += 1
                
                # If we ran out of models, wait and reset to top
                if current_model_index >= len(GEMMA_MODELS):
                    print("Smart Renamer: All models exhausted. Waiting 10s...")
                    time.sleep(10)
                    current_model_index = 0
                
                retry_count += 1
                # Loop continues immediately with new model
            else:
                # Success or other error
                success = True
                result_queue.put(result)
                if 'new_name' in result:
                    recent_names.append(result['new_name'])
        
        task_queue.task_done()
        # No sleep here! We go as fast as possible.

    print("Smart Renamer: Batch worker finished.")

def process_queue_timer():
    """
    Timer function to check the result queue and update Blender objects.
    """
    try:
        while not result_queue.empty():
            item = result_queue.get_nowait()
            
            obj_name = item.get('obj_name')
            new_name = item.get('new_name')
            error = item.get('error')
            
            if obj_name in bpy.data.objects:
                obj = bpy.data.objects[obj_name]
                
                if error:
                    print(f"Smart Renamer Error for {obj_name}: {error}")
                elif new_name:
                    old_name = obj.name
                    obj.name = new_name
                    print(f"Smart Renamer: Renamed '{old_name}' to '{new_name}'")
            
    except queue.Empty:
        pass
        
    return 1.0  # Run again in 1 second

class SMART_RENAMER_OT_analyze_rename(bpy.types.Operator):
    """Analyze and Rename Object using AI"""
    bl_idname = "smart_renamer.analyze_rename"
    bl_label = "Analyze & Rename"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        
        # Get API Key from Addon Preferences
        addon_prefs = context.preferences.addons.get(__package__).preferences
        api_key = addon_prefs.api_key
        
        naming_style = scene.smart_renamer_naming_style
        context_text = getattr(scene, "smart_renamer_context", "")
        view_mode = getattr(scene, "smart_renamer_view_mode", 'FRONT_BACK')
        include_context = getattr(scene, "smart_renamer_include_context", True)
        
        if not api_key:
            self.report({'ERROR'}, "Please configure API Key in Addon Preferences")
            # Open preferences for the user
            bpy.ops.preferences.addon_show(module=__package__)
            return {'CANCELLED'}
            
        # Validate API Key
        if any(c.isspace() for c in api_key.strip()):
            self.report({'ERROR'}, "Invalid API Key: Contains spaces. Please check your key.")
            bpy.ops.preferences.addon_show(module=__package__)
            return {'CANCELLED'}
            
        # Determine objects to process
        objects_to_process = [o for o in context.selected_objects if o.type == 'MESH']
            
        if not objects_to_process:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}
            
        # Register timer if not already running
        if not bpy.app.timers.is_registered(process_queue_timer):
            bpy.app.timers.register(process_queue_timer)
            
        # 1. Capture all images first (Main Thread)
        tasks_added = 0
        for obj in objects_to_process:
            images_b64 = []
            
            # Front View (Always captured)
            image_iso_front_path = utils.take_isolated_screenshot(obj, context, view_angle='FRONT')
            if image_iso_front_path:
                images_b64.append(utils.image_to_base64(image_iso_front_path))
            
            # Back View (Optional)
            if view_mode == 'FRONT_BACK':
                image_iso_back_path = utils.take_isolated_screenshot(obj, context, view_angle='BACK')
                if image_iso_back_path:
                    images_b64.append(utils.image_to_base64(image_iso_back_path))
            
            # Context View (Optional)
            if include_context:
                image_ctx_path = utils.take_context_screenshot(obj, context)
                if image_ctx_path:
                    images_b64.append(utils.image_to_base64(image_ctx_path))
            
            if not images_b64:
                print(f"Skipping {obj.name}: Image capture failed.")
                continue
            
            # Gather Object Metadata
            collection_name = obj.users_collection[0].name if obj.users_collection else "Scene Collection"
            dims = obj.dimensions
            dimensions_str = f"{dims.x:.2f}m x {dims.y:.2f}m x {dims.z:.2f}m"
            
            # Add to task queue
            task_queue.put({
                'obj_name': obj.name,
                'images_b64': images_b64,
                'context': context_text,
                'collection_name': collection_name,
                'dimensions': dimensions_str
            })
            tasks_added += 1
            
        if tasks_added == 0:
            self.report({'ERROR'}, "No images could be captured.")
            return {'CANCELLED'}

        # 2. Start ONE worker thread to process the queue
        # Only start if not already running (simple check: if queue was empty before, we might need to start it)
        # But since we just filled it, we can just start a thread. 
        # Note: If a thread is already running from a previous click, it will just pick up these new tasks 
        # because it loops `while not task_queue.empty()`.
        # However, if the previous thread finished, we need a new one.
        # A simple way is to check if the queue size is exactly what we added (meaning it was empty).
        # Or just start a thread and let it check. 
        # To avoid multiple threads racing, we can check active threads, but `task_queue` is thread-safe.
        # If multiple threads run, we hit rate limits. 
        # Ideally we want a singleton worker.
        
        # Simple Singleton Pattern for Worker:
        # Check if we have a living worker thread? 
        # For simplicity in this script, we'll just start a thread. 
        # If the user clicks twice rapidly, we might get 2 threads and hit 429.
        # But assuming reasonable usage:
        
        thread = threading.Thread(
            target=batch_worker,
            args=(api_key, naming_style)
        )
        thread.daemon = True
        thread.start()
            
        self.report({'INFO'}, f"Queued {tasks_added} objects for analysis...")
        return {'FINISHED'}
