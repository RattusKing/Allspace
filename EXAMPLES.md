# 📸 Example Images and Results

This document shows example images you can use to test Allspace (Floor Plan to 3D Model Converter) and what to expect.

## 🧪 Test Images

### Best Results

The converter works best with:

1. **Floor Plans**
   - Dark walls on a clean, light/white background
   - Clear, high-contrast line work
   - Standard architectural drawing style near a single scale/DPI

### Example Workflow

1. **Input**: A floor plan image (dark walls on a light background)
   - Classical OpenCV thresholds the dark pixels into a binary wall mask
   - The wall mask is traced and its edges are extruded into vertical 3D walls
   - Door/window openings are detected and per-room floor tiles are added
   - The result is exported as a GLB you can preview and download

## 📊 Expected Results

### Processing Time
- **512x512 image**: ~30 seconds
- **1024x1024 image**: ~60 seconds
- **2048x2048 image**: ~90-120 seconds

### Output Quality

**GLB File**
- Size: 1-5 MB typically
- Optimized for web viewers (Google `<model-viewer>`) and other glTF-compatible tools

**OBJ File**
- Plain-text OBJ with per-vertex colors, for Blender, Unity, and Unreal
- (Note: there is no FBX export — trimesh cannot author FBX. OBJ imports into the same tools.)

## 🎯 Tips for Best Results

1. **Drawing Quality**
   - Clear walls with good contrast work best. Blueprints (light walls on a dark
     ground) and grey/low-contrast walls are now handled automatically.
   - Remove or minimize furniture, text, and dimension lines if you can — most are
     filtered out, but heavy annotation can still leak into the walls
   - If your plan isn't detected correctly, set **Input type → Force floor plan**

2. **Scale**
   - Leave scale on `auto` for a normalized footprint, or supply a numeric scale ratio for floor plans to get approximate real-world dimensions (assumes 96 DPI)

3. **Resolution**
   - Inputs are processed at up to ~1024px internally; extremely thin CAD lines survive better in a clean, bold plan. Use the **High** complexity option to keep the most wall detail.

## 🖼️ Sample Images to Try

You can test with:
- Architectural floor plans
- Simple hand-drawn or CAD-style room layouts (dark walls, light background)

## ⚠️ Limitations

**May Not Work Well With:**
- Blueprints (light lines on a dark background)
- Colored / real-estate-style plans (can misclassify as a photo)
- Gray-filled or very thin walls
- Photographed plans with uneven lighting
- Plans dense with furniture, text, or dimension lines

See `FLOORPLAN-DIAGNOSIS.md` for full details on these limits.

## 🎨 Uses

**Architecture / Real Estate**
```
Floor Plan → 3D Model → Client Review
```

**Import into other tools**
```
Floor Plan → GLB → Blender / Unity / Unreal
```

## 📝 Sharing Results

If you create something cool:
1. Export the model
2. Take a screenshot
3. Share on GitHub Discussions
4. Help others learn!

## 🤝 Community Examples

We'd love to see what you create! Share your results:
- Open a discussion on GitHub
- Tag us on social media
- Contribute to the wiki with your examples

---

**Remember**: This is a classical computer-vision tool (OpenCV on the CPU — no AI, no GPU, no model downloads). It works best on clean floor plans with dark walls on a light background, and results vary with drawing style, resolution, and scale. See `FLOORPLAN-DIAGNOSIS.md` for the known accuracy limits.
