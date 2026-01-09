### Video Title Ideas:
- "Smart Renamer: AI That Actually Helps Artists (Instead of Replacing Them)"
- "Stop Naming 'Cube.001' – Let AI Do the Boring Stuff in Blender"
- "The AI Tool That Makes 3D Artists Happier (And Faster)"

### Video Description (for SEO):
"Discover Smart Renamer, the Blender addon that uses AI to automatically rename your 3D objects. No more messy outliners! Try the free lite version for single objects, then upgrade for batch processing. Download links in bio. #Blender #AI #3DArt #GameDev"

### Thumbnail Ideas:
- Split-screen: Messy outliner on left ("Before"), clean outliner on right ("After")
- Text overlay: "AI Renames Your Objects Instantly"
- Your face with a smile, pointing to a clean Blender scene

---

### Script: "Smart Renamer: AI That Actually Helps Artists"

**[0:00 – 0:25] Intro Hook (The Community Pain & Personal Story)**  
**[Visuals]**  
- Open Blender with a cluttered Outliner: `Cube.001`, `Cylinder.045`, `Plane.999`, etc.  
- Zoom in on the mess, then cut to you looking frustrated at the screen.  
- Quick montage: Show 2-3 real Blender memes (e.g., "When your outliner looks like this" with chaotic names, or "Naming objects: The eternal struggle"). Source from Reddit or stock images.  
- Text overlay: "The Boring Part of 3D Art"  

**[Audio]**  
"Hey everyone, welcome to the channel! If you're a 3D artist, you probably know the pain of renaming meshes in the outliner—so much so it became a meme across the community. [Pause to show memes on screen.]  

I personally try my best to correctly name everything when I work on assets, but sometimes when you're too focused on the project, you can end up with an outliner looking like this—and it happened to me so many times. When you're looking for an object in the modifier's list of targets or trying to find one specific object in the outliner, especially when it's packed, it can be really annoying.  

And it's until recently I told myself, 'That's something that can be automated, and it would save artists a lot of time.' So, I built Smart Renamer, a Blender addon that uses computer vision to see your objects and rename them automatically. And I think this is the best use of AI—helping artists by doing the annoying parts and letting them do the creative fun part, instead of using it to generate art. Let's dive in!"

**[0:25 – 0:55] How It Works (The Solution)**  
**[Visuals]**  
- Split-screen demo: Left side shows a standard renamer (renaming everything to "Asset_01"). Right side shows Smart Renamer analyzing and renaming to specific names like "SciFi_Crate", "Metal_Barrel", "Wooden_Plank".  
- Show the "Toy Boat vs. Cargo Ship" example: Two similar objects, but AI distinguishes based on scale.  
- Text overlay: "AI Sees What You See"  

**[Audio]**  
"So how does it work? It's very different from the existing renaming tools—instead, you can tell the AI to recognize the objects and rename them accordingly, or to give specific instructions on how they should be renamed. Smart Renamer takes a quick screenshot of your object, analyzes its geometry, style, and even the context around it, and generates a professional name, based on naming conventions.  

For example, it knows the difference between a tiny 'Toy Boat' and a massive 'Cargo Ship' because it checks the scale. And it does this using Google's Gemma 3 vision models—open-source AI."

**[0:55 – 2:15] Step-by-Step Tutorial (Full Version)**  
**[Visuals]**  
- Screen recording of Blender UI. Zoom in on the N-Panel (Smart Renamer tab).  
- Demonstrate selecting objects, choosing styles, adding context, and clicking "Analyze & Rename".  
- Show progress bar updating in real-time.  
- Highlight naming styles: Snake_Case, Unreal Engine, etc.  
- Show the cancel button if needed.  

**[Audio]**  
"Alright, let's get hands-on. First, download the addon from the link in the description—there's a free lite version to try on single objects, and the full version for batch processing.  
To install it, go to Blender's Edit menu > Preferences > Add-ons, and install the zip file. Then, you'll need a free API key from Google Gemini—either click the link in the description or readme file, or just search 'Gemini API' on Google to get to Google AI Studio. Sign up, create a project, and generate your free API key. Then paste it into the API key field in the addon's preferences.  
Step 1: Select your objects. You can rename hundreds at once in the full version.  
Step 2: Choose your naming style. Game    devs might want Snake_Case or Unreal Engine prefixes.  
Step 3: Add context—type something like 'Sci-Fi spaceship parts' to guide the AI.  
Step 4: Configure views—'Front Only' for speed, or 'Front & Back' for accuracy.  
Step 5: Click 'Analyze & Rename'. It processes in the background, so you can keep working. There's even a cancel button if you change your mind.  

Watch this—my messy outliner transforms into 'SM_SciFi_Crate_01', 'Engine_Piston_02', and so on. It's like having an assistant who understands 3D art!"

**[2:15 – 3:00] Advanced Features & Lite Version Teaser**  
**[Visuals]**  
- Show consistency engine: Identical objects get matching names.  
- Demo fast mode toggle.  
- Cut to lite version UI: Simpler, single-object only.  
- Text overlay: "Try Free – Upgrade for More"  

**[Audio]**  
"The full version has some killer features. The consistency engine remembers names—if it calls one bolt 'Metal_Bolt', it won't name the next 'Industrial_Fastener'. Fast mode uses quicker models for massive batches. And it handles rate limits gracefully by switching models automatically.  

But if you're new to this, start with the free lite version. It lets you rename one object at a time to test the AI. Once you see how it turns 'Cube.001' into 'Vintage_Chair', you'll want the full thing for unlimited batch processing."

**[3:00 – 3:45] Privacy & Ethics (Building Trust)**  
**[Visuals]**  
- Face cam: You looking sincere.  
- Text overlay: "Your Models Stay Private"  
- Quick animation: Screenshot vs. 3D model (showing only pixels are sent).  

**[Audio]**  
"Now, I know what you're thinking—'Is this uploading my 3D models?' Absolutely not. Smart Renamer only sends low-resolution screenshots (256 pixels) of your viewport. It's impossible to steal your geometry, UVs, or textures from a tiny image. Your work stays on your machine.  

And ethically, this is AI done right. It's not generating art for you—it's automating the admin so you can focus on the creative stuff. I think this is the best use of AI, helping artists by doing the annoying parts and letting them do the creative and fun part, instead of using it to generate art. It's a tool, not a replacement."

**[3:45 – 4:30] Setup & Pricing**  
**[Visuals]**  
- Quick steps: Go to Google AI Studio, get free API key, paste in Blender preferences.  
- Show pricing: $15 standard, $45 studio.  
- Gumroad/Blender Market links.  

**[Audio]**  
"Setup is easy—get a free Google Gemini API key (takes 2 minutes), paste it in the addon preferences, and you're good. The free tier handles most daily use.  

Pricing: $15 for individuals, $45 for studios. It's a one-time purchase with lifetime updates. If it doesn't save you time, there's a 30-day refund guarantee."

**[4:30 – 5:00] Outro & Call to Action**  
**[Visuals]**  
- Montage of clean outliners, happy artists working.  
- End screen: Links to download, subscribe, like.  

**[Audio]**  
"So, if you're tired of naming cubes, give Smart Renamer a try. Download the free lite version first, see the magic, then upgrade for the full power. Link in the description—let me know in the comments if you've tried AI tools like this before.  

Thanks for watching, and happy blending! If this helped, smash that like button and subscribe for more Blender tips."

---

### Production Tips:
- **Length:** Now about 5:00–5:15 minutes. The memes add visual interest—use public domain or fair-use clips from Reddit (e.g., r/blender memes).
- **Meme Sources:** Search for "Blender outliner memes" on Google Images or Reddit. Keep them short (2-3 seconds each) to avoid copyright issues.
- **Flow:** The community pain → memes → personal story creates a strong hook that resonates with the audience.
- **Editing:** Add humorous sound effects during memes for laughs.
- **Engagement:** Ask viewers to share their favorite memes in comments.

This version balances community relatability with your personal touch. If you need further tweaks, let me know!
