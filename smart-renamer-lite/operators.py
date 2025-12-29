import bpy
import json
import urllib.request
import urllib.error
from . import utils

# Available models (lite version uses only 4b for speed)
GEMMA_MODELS = [
    "gemma-3-4b-it"
]

NAMING_STYLE_DESCRIPTIONS = {
    'Snake_Case': "lowercase words separated by underscores (e.g., `sci_fi_crate`).",
    'CamelCase': "Capitalized words concatenated without spaces (PascalCase) (e.g., `SciFiCrate`).",
    'lowerCamelCase': "First word lowercase, subsequent words capitalized (e.g., `sciFiCrate`).",
    'UPPER_SNAKE_CASE': "Uppercase words separated by underscores (e.g., `SCI_FI_CRATE`).",
    'Kebab-Case': "Lowercase words separated by hyphens (e.g., `sci-fi-crate`).",
    'Unreal_Prefix': "Asset type prefix followed by PascalCase (e.g., `SM_Crate` for static meshes).",
    'Descriptive': "A short, natural language description (e.g., `Old Wooden Crate`)."
}

def send_gemini_request(api_key, images_b64, naming_style, obj_name, model_name, context_text="", collection_name="", dimensions=""):
    """
    Sends request to Gemini API. Returns dict with result or error code.
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
        return {'obj_name': obj_name, 'error': f"API Error {e.code}: {e.reason}"}
    except ValueError as e:
        return {'obj_name': obj_name, 'error': f"Invalid API Key or URL: {str(e)}"}
    except Exception as e:
        return {'obj_name': obj_name, 'error': str(e)}

class SMART_RENAMER_OT_analyze_rename(bpy.types.Operator):
    """Analyze and Rename Object using AI (Lite Version - Single Object Only)"""
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

        # Determine objects to process - ONLY ONE OBJECT ALLOWED
        selected_meshes = [o for o in context.selected_objects if o.type == 'MESH']

        if len(selected_meshes) != 1:
            self.report({'ERROR'}, "Smart Renamer Lite: Please select exactly ONE mesh object")
            return {'CANCELLED'}

        obj = selected_meshes[0]

        # Update UI status
        scene.smart_renamer_is_processing = True
        scene.smart_renamer_status = "Capturing images..."

        # Force UI update
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        try:
            # Capture images for the single object
            images_b64 = []

            # Use CaptureSession to optimize state saving/restoring
            with utils.CaptureSession(context) as session:
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
                self.report({'ERROR'}, "Failed to capture images")
                scene.smart_renamer_is_processing = False
                scene.smart_renamer_status = "Failed"
                return {'CANCELLED'}

            # Gather Object Metadata
            collection_name = obj.users_collection[0].name if obj.users_collection else "Scene Collection"
            dims = obj.dimensions
            dimensions_str = f"{dims.x:.2f}m x {dims.y:.2f}m x {dims.z:.2f}m"

            # Update status
            scene.smart_renamer_status = "Analyzing..."

            # Force UI update
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

            # Send API request directly (no threading needed for single object)
            result = send_gemini_request(
                api_key, images_b64, naming_style, obj.name, GEMMA_MODELS[0],
                context_text, collection_name, dimensions_str
            )

            # Process result
            if result.get('error'):
                self.report({'ERROR'}, f"Smart Renamer Error: {result['error']}")
                scene.smart_renamer_is_processing = False
                scene.smart_renamer_status = "Error"
                return {'CANCELLED'}
            elif result.get('new_name'):
                old_name = obj.name
                obj.name = result['new_name']
                self.report({'INFO'}, f"Renamed '{old_name}' to '{result['new_name']}'")
                scene.smart_renamer_is_processing = False
                scene.smart_renamer_status = "Done!"
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Unexpected API response")
                scene.smart_renamer_is_processing = False
                scene.smart_renamer_status = "Error"
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Unexpected error: {str(e)}")
            scene.smart_renamer_is_processing = False
            scene.smart_renamer_status = "Error"
            return {'CANCELLED'}
