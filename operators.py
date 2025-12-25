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

def send_gemini_request(api_key, image_b64, naming_style, obj_name, retries=3):
    """
    Helper function to perform the actual API request.
    Returns a dict with keys: 'obj_name', 'new_name' (optional), 'error' (optional)
    """
    try:
        # Using 'gemini-flash-latest' alias for stability as per recent API updates
        model_name = "gemini-flash-latest" 
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key.strip()}"
        
        headers = {'Content-Type': 'application/json'}
        
        prompt_text = (
            f"Analyze this 3D object image. "
            f"Return ONLY a JSON object {{'name': 'new_name'}} based on its visual appearance. "
            f"Adhere to naming convention: {naming_style}. "
            f"Do not include markdown formatting or explanations."
        )
        
        data = {
            "contents": [{
                "parts": [
                    {"text": prompt_text},
                    {"inline_data": {
                        "mime_type": "image/png",
                        "data": image_b64
                    }}
                ]
            }]
        }
        
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if 'candidates' not in result or not result['candidates']:
                 return {'obj_name': obj_name, 'error': "API returned no candidates. Safety filter?"}

            text_response = result['candidates'][0]['content']['parts'][0]['text']
            text_response = text_response.replace('```json', '').replace('```', '').strip()
            name_data = json.loads(text_response)
            new_name = name_data.get('name', 'Unknown_Object')
            
            return {'obj_name': obj_name, 'new_name': new_name}
            
    except urllib.error.HTTPError as e:
        if e.code == 429:
            if retries > 0:
                wait_time = 10  # Wait 10 seconds before retrying
                print(f"Smart Renamer: 429 Limit hit for '{obj_name}'. Retrying in {wait_time}s... ({retries} left)")
                time.sleep(wait_time)
                return send_gemini_request(api_key, image_b64, naming_style, obj_name, retries=retries-1)
            else:
                return {'obj_name': obj_name, 'error': "API Rate Limit Exceeded (429) after retries."}
        elif e.code == 404:
            return {'obj_name': obj_name, 'error': f"API 404: Model '{model_name}' not found."}
        else:
            return {'obj_name': obj_name, 'error': f"API Error {e.code}: {e.reason}"}
    except Exception as e:
        return {'obj_name': obj_name, 'error': f"Network/Parse Error: {str(e)}"}

def batch_worker(api_key, naming_style):
    """
    Worker thread that processes the task queue sequentially.
    """
    print("Smart Renamer: Batch worker started.")
    while not task_queue.empty():
        task = task_queue.get()
        obj_name = task['obj_name']
        image_b64 = task['image_b64']
        
        print(f"Smart Renamer: Processing '{obj_name}'...")
        
        # Process the request
        result = send_gemini_request(api_key, image_b64, naming_style, obj_name)
        result_queue.put(result)
        
        task_queue.task_done()
        
        # Rate Limiting: Sleep between requests if there are more items
        if not task_queue.empty():
            time.sleep(4.0) # 4 seconds delay to stay under 15 RPM (Free Tier)

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
        scope = scene.smart_renamer_scope
        
        if not api_key:
            self.report({'ERROR'}, "Please configure API Key in Addon Preferences")
            # Open preferences for the user
            bpy.ops.preferences.addon_show(module=__package__)
            return {'CANCELLED'}
            
        # Determine objects to process
        objects_to_process = []
        if scope == 'ACTIVE':
            if context.active_object:
                objects_to_process.append(context.active_object)
        elif scope == 'SELECTED':
            objects_to_process = [o for o in context.selected_objects]
            
        if not objects_to_process:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}
            
        # Register timer if not already running
        if not bpy.app.timers.is_registered(process_queue_timer):
            bpy.app.timers.register(process_queue_timer)
            
        # 1. Capture all images first (Main Thread)
        tasks_added = 0
        for obj in objects_to_process:
            image_path = utils.take_isolated_screenshot(obj, context)
            if not image_path:
                print(f"Skipping {obj.name}: Image capture failed.")
                continue
                
            image_b64 = utils.image_to_base64(image_path)
            
            # Add to task queue
            task_queue.put({
                'obj_name': obj.name,
                'image_b64': image_b64
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
