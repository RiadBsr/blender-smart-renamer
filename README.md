# Smart Renamer for Blender

**Smart Renamer** is an advanced AI-powered addon that automatically renames your 3D objects using Google's Gemini Vision models. It "sees" your objects just like a human would to generate precise, consistent, and professional names.

## Key Features

*   **AI Vision Analysis**: Uses Google's **Gemma 3** vision models to understand 3D geometry.
*   **Context-Aware**: Captures not just the object, but its surroundings (using X-Ray/Wireframe overlays) to understand scale and usage.
*   **Multi-View Capture**: Automatically takes Front and Back isolated views for 360° understanding.
*   **Smart Batch Processing**: Renames hundreds of objects efficiently using a cascading model strategy (27b → 1b) to maximize speed and handle rate limits.
*   **Consistency Engine**: Remembers names used within the current batch to ensure identical objects get identical names (e.g., naming all "Pistons" consistently instead of mixing "Piston", "Cylinder", and "EnginePart").
*   **Professional Naming Conventions**: Supports Snake_Case, CamelCase, Unreal Engine Prefixes (SM_), and Descriptive styles.

## Installation

1.  Download the `SmartRenamer_v1.0.zip` file.
2.  Open Blender and go to **Edit > Preferences**.
3.  Select the **Add-ons** tab and click **Install...**.
4.  Locate the zip file and click **Install Add-on**.
5.  Enable the checkbox next to **Object: Smart Renamer**.

## Configuration

Before using the addon, you need a free Google Gemini API Key.

1.  Go to [Google AI Studio](https://aistudio.google.com/app/apikey) and create an API Key.
2.  In Blender, go to the **Smart Renamer** addon preferences (or click "Open Preferences" in the addon panel).
3.  Paste your API Key into the field.

## Usage

The addon is located in the **3D Viewport Sidebar (N-Panel)** under the **Smart Renamer** tab.

1.  **Select Objects**: Select one or more mesh objects you want to rename.
2.  **Choose Style**: Select your preferred naming convention (e.g., `Snake_Case` for `sci_fi_crate`).
3.  **Add Context (Optional)**: Type a hint in the "Context" box to guide the AI (e.g., *"Low poly game assets"*, *"Car engine parts"*).
4.  **Configure Capture**:
    *   **Views**: Choose "Front Only" for speed or "Front & Back" for accuracy.
    *   **Include Scene Context**: Toggle this on to let the AI see where the object fits in the scene.
5.  **Click "Analyze & Rename"**: The addon will process the queue in the background. You can continue working while it runs!

## Tips for Best Results

*   **Use the Context Box**: If you are renaming parts of a specific asset, tell the AI!
    *   *Example:* "Medieval castle kitbash set"
    *   *Example:* "Spaceship landing gear details"
*   **Batch Similar Objects**: Select all parts of a model at once. The AI shares context between them to maintain naming consistency.
*   **Check Dimensions**: The addon automatically sends object dimensions to the AI, so it knows the difference between a "Toy Boat" (10cm) and a "Cargo Ship" (100m).
*   **Collection Names**: Organizing the objects inside correctly named collections can help the AI understand better.

## Requirements

*   Blender 2.80 or later.
*   Active Internet connection (for API access).
*   Valid Google Gemini API Key.

## License

MIT License. Free to use for personal and commercial projects.