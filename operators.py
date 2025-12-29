import bpy
import threading
import queue
import json
import urllib.request
import urllib.error
import time
import random
from . import utils

# Global queues
# result_queue: passes results from worker thread to main thread (Blender)
result_queue = queue.Queue()
# task_queue: holds pending API requests to be processed sequentially
task_queue = queue.Queue()

# Global Progress Tracking
pending_tasks_count = 0
total_tasks_count = 0

# Gemma 3 Family - Available models (removed 2b and 1b as they return 404)
GEMMA_MODELS = [
    "gemma-3-27b-it",
    "gemma-3-12b-it",
    "gemma-3-4b-it"
]

# Rate-limit helpers (per-model cooldowns + counters)
model_429_counts = {m: 0 for m in GEMMA_MODELS}
model_cooldowns = {m: 0.0 for m in GEMMA_MODELS}  # timestamp until which model is paused
backoff_until = 0.0  # global pause timestamp when all models exhausted
cooldown_lock = threading.Lock()

NAMING_STYLE_DESCRIPTIONS = {
    'Snake_Case': "lowercase words separated by underscores (e.g., `sci_fi_crate`).",
    'CamelCase': "Capitalized words concatenated without spaces (PascalCase) (e.g., `SciFiCrate`).",
    'lowerCamelCase': "First word lowercase, subsequent words capitalized (e.g., `sciFiCrate`).",
    'UPPER_SNAKE_CASE': "Uppercase words separated by underscores (e.g., `SCI_FI_CRATE`).",
    'Kebab-Case': "Lowercase words separated by hyphens (e.g., `sci-fi-crate`).",
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
        
        # Concise prompt to reduce token usage while preserving rules
        prompt_text = (
            "You are an expert 3D Technical Artist. Analyze the provided images and metadata, "
            "then return ONLY a JSON object: {\"name\": \"...\"}.\n"
            f"Style: {naming_style} ({style_desc}). Be concise and descriptive; avoid generic names and colors.\n"
            "Use the object's current name, collection, and dimensions to infer scale and role.\n"
        )

        if context_text:
            prompt_text += f"Project Context: {context_text}.\n"

        if recent_names:
            # Keep recent names short to save tokens
            recent_snippet = ', '.join(recent_names[-6:])
            prompt_text += (
                f"Batch Context (use for consistency only): {recent_snippet}. "
                "Do not copy names for different objects.\n"
            )
        
        # Estimate Token Usage for logging
        # Gemini Vision typically counts images as 258 tokens each
        # Text is approx 1 token per 4 chars
        # num_images = len([img for img in images_b64 if img])
        # est_image_tokens = num_images * 258
        # est_text_tokens = len(prompt_text) // 4
        # total_est_tokens = est_image_tokens + est_text_tokens
        
        # print(f"Smart Renamer: Sending request (~{total_est_tokens} tokens) to {model_name}...")
        
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

def batch_worker(api_key, naming_style, shared_recent_names, names_lock, fast_mode=False):
    global backoff_until
    # print("Smart Renamer: Batch worker started.")
    
    # Start with 27b for standard (quality), 4b for fast mode (speed)
    current_model_index = 0 if not fast_mode else 2
    
    while True:
        try:
            item = task_queue.get_nowait()
        except queue.Empty:
            break
            
        obj_name = item['obj_name']
        images_b64 = item['images_b64']
        context_text = item.get('context', "")
        collection_name = item.get('collection_name', "")
        dimensions = item.get('dimensions', "")
        
        # Get recent names safely
        with names_lock:
            current_context_names = list(shared_recent_names)
        
        # Try to process
        success = False
        retry_count = 0
        
        while not success and retry_count < len(GEMMA_MODELS) + 1:
            # Find the next available model that is not on cooldown
            with cooldown_lock:
                now = time.time()
                searched = 0
                # Advance current_model_index until we find a model not in cooldown
                while searched < len(GEMMA_MODELS):
                    candidate = GEMMA_MODELS[current_model_index % len(GEMMA_MODELS)]
                    if model_cooldowns.get(candidate, 0.0) <= now:
                        break
                    current_model_index += 1
                    searched += 1

                # If all models are on cooldown, respect global backoff
                if searched >= len(GEMMA_MODELS):
                    # set a small jittered pause before retrying
                    pause = max(1.0, (2 ** min(retry_count, 4))) + random.random()
                    # print(f"Smart Renamer: All models on cooldown. Global backoff for {pause:.1f}s...")
                    with cooldown_lock:
                        backoff_until = time.time() + pause
                    time.sleep(pause)
                    # reset index to start
                    current_model_index = 0 if not fast_mode else 2

            current_model = GEMMA_MODELS[current_model_index % len(GEMMA_MODELS)]
            # print(f"Smart Renamer: Processing '{obj_name}' using {current_model}...")
            
            result = send_gemini_request(
                api_key, images_b64, naming_style, obj_name, current_model, 
                context_text, collection_name, dimensions, current_context_names
            )
            
            if result.get('status_code') == 429:
                # print(f"Smart Renamer: Rate limit hit on {current_model}. Applying cooldown and downgrading...")
                # Register the 429 for this model and apply exponential cooldown
                with cooldown_lock:
                    model_429_counts[current_model] = model_429_counts.get(current_model, 0) + 1
                    # exponential base cooldown (seconds) with cap
                    base = 2.0
                    exp = min(model_429_counts[current_model], 6)
                    cooldown = base * (2 ** (exp - 1))
                    # add small jitter to avoid sync storms
                    cooldown += random.uniform(0.5, 1.5)
                    model_cooldowns[current_model] = time.time() + cooldown
                    # print(f"Smart Renamer: {current_model} cooled down for {cooldown:.1f}s (count={model_429_counts[current_model]})")

                # Move to next model in chain (upgrade for fast, downgrade for standard)
                if fast_mode:
                    current_model_index -= 1
                else:
                    current_model_index += 1

                # If we've cycled through all models without success, apply a global backoff
                if current_model_index < 0 or current_model_index >= len(GEMMA_MODELS):
                    global_pause = max(5.0, 2 ** min(retry_count, 6)) + random.random()
                    # print(f"Smart Renamer: All models exhausted. Global pause {global_pause:.1f}s...")
                    with cooldown_lock:
                        backoff_until = time.time() + global_pause
                    time.sleep(global_pause)
                    current_model_index = 0 if not fast_mode else 2

                retry_count += 1
                # Loop continues immediately with new model
            else:
                # Success or other error
                success = True
                result_queue.put(result)
                if 'new_name' in result:
                    with names_lock:
                        shared_recent_names.append(result['new_name'])
                # Small spacing between successful requests to reduce bursts
                time.sleep(random.uniform(0.05, 0.25))
        
        task_queue.task_done()
        # No sleep here! We go as fast as possible.

    # print("Smart Renamer: Batch worker finished.")

def process_queue_timer():
    """
    Timer function to check the result queue and update Blender objects.
    """
    global pending_tasks_count, total_tasks_count
    
    try:
        # Process all available results
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
            
            pending_tasks_count -= 1
            
        # Update Status
        if pending_tasks_count > 0:
            completed = total_tasks_count - pending_tasks_count
            bpy.context.scene.smart_renamer_status = f"Processing... ({completed}/{total_tasks_count})"
            bpy.context.scene.smart_renamer_is_processing = True
        elif total_tasks_count > 0 and pending_tasks_count <= 0:
            # All done
            bpy.context.scene.smart_renamer_status = f"Done! ({total_tasks_count} processed)"
            bpy.context.scene.smart_renamer_is_processing = False
            # Reset counters after a brief delay or immediately? 
            # Let's leave the "Done" message visible.
            # We can reset total_tasks_count to 0 to stop this block from running repeatedly,
            # but we want to keep the "Done" message.
            # So we just set is_processing to False.
            
    except queue.Empty:
        pass
        
    return 0.5  # Run again in 0.5 seconds (faster updates)

class SMART_RENAMER_OT_analyze_rename(bpy.types.Operator):
    """Analyze and Rename Object using AI"""
    bl_idname = "smart_renamer.analyze_rename"
    bl_label = "Analyze & Rename"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global pending_tasks_count, total_tasks_count
        scene = context.scene
        
        # Get API Key from Addon Preferences
        addon_prefs = context.preferences.addons.get(__package__).preferences
        api_key = addon_prefs.api_key
        
        naming_style = scene.smart_renamer_naming_style
        context_text = getattr(scene, "smart_renamer_context", "")
        view_mode = getattr(scene, "smart_renamer_view_mode", 'FRONT_BACK')
        include_context = getattr(scene, "smart_renamer_include_context", True)
        fast_mode = getattr(scene, "smart_renamer_fast_mode", False)
        
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
            
        # Initialize Progress
        total_tasks_count = len(objects_to_process)
        pending_tasks_count = total_tasks_count
        scene.smart_renamer_is_processing = True
        scene.smart_renamer_status = "Capturing images..."
        
        # Force UI update so the user sees the status change before freezing
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        
        # Register timer if not already running
        if not bpy.app.timers.is_registered(process_queue_timer):
            bpy.app.timers.register(process_queue_timer)
            
        # 1. Capture all images first (Main Thread)
        tasks_added = 0
        
        # Use CaptureSession to optimize state saving/restoring
        with utils.CaptureSession(context) as session:
            for obj in objects_to_process:
                images_b64 = []
                
                # Front View (Always captured)
                image_iso_front_path = utils.take_isolated_screenshot(obj, context, view_angle='FRONT', session=session)
                if image_iso_front_path:
                    images_b64.append(utils.image_to_base64(image_iso_front_path))
                
                # Back View (Optional)
                if view_mode == 'FRONT_BACK':
                    image_iso_back_path = utils.take_isolated_screenshot(obj, context, view_angle='BACK', session=session)
                    if image_iso_back_path:
                        images_b64.append(utils.image_to_base64(image_iso_back_path))
                
                # Context View (Optional)
                if include_context:
                    image_ctx_path = utils.take_context_screenshot(obj, context, session=session)
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
            
        # Update pending count to match actual tasks added
        pending_tasks_count = tasks_added
        total_tasks_count = tasks_added
        
        if tasks_added == 0:
            self.report({'ERROR'}, "No images could be captured.")
            scene.smart_renamer_is_processing = False
            scene.smart_renamer_status = "Failed"
            return {'CANCELLED'}
            
        scene.smart_renamer_status = f"Processing... (0/{total_tasks_count})"

        # 2. Start worker threads
        shared_recent_names = []
        names_lock = threading.Lock()
        
        # Spin up 2 workers for parallel processing
        # This doubles throughput but increases risk of 429 errors.
        # The fallback strategy in batch_worker handles 429s by switching models.
        num_workers = 2
        
        for _ in range(num_workers):
            thread = threading.Thread(
                target=batch_worker,
                args=(api_key, naming_style, shared_recent_names, names_lock, fast_mode)
            )
            thread.daemon = True
            thread.start()
            
        self.report({'INFO'}, f"Queued {tasks_added} objects for analysis...")
        return {'FINISHED'}

class SMART_RENAMER_OT_cancel_process(bpy.types.Operator):
    """Cancel the current renaming process"""
    bl_idname = "smart_renamer.cancel_process"
    bl_label = "Cancel"
    bl_options = {'REGISTER'}

    def execute(self, context):
        global pending_tasks_count, total_tasks_count
        
        # Clear the task queue
        while not task_queue.empty():
            try:
                task_queue.get_nowait()
                task_queue.task_done()
            except queue.Empty:
                break
        
        # Reset counters
        pending_tasks_count = 0
        total_tasks_count = 0
        
        # Update UI
        context.scene.smart_renamer_is_processing = False
        context.scene.smart_renamer_status = "Cancelled"
        
        self.report({'INFO'}, "Smart Renamer process cancelled.")
        return {'FINISHED'}
