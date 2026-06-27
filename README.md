# 🏠 Allspace — Floor Plan to 3D Model Converter

Turn a 2D floor plan image into a 3D architectural model using classical computer vision — no AI, no GPU, no model downloads. Upload a plan, get walls extruded into real 3D geometry, preview it in your browser, and export to GLB.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)](https://flask.palletsprojects.com/)

## ✨ Features

- 🏗️ **Floor Plan → 3D** - Upload a 2D floor plan and get a 3D model with extruded walls, per-room floors, and detected door/window openings
- 🧮 **Classical Computer Vision** - Pure OpenCV image processing on the CPU. No neural networks, no MiDaS, no PyTorch, no GPU required
- 📦 **GLB + OBJ Export** - Download a GLB (glTF Binary) model for web viewers, or an OBJ for Unity, Unreal Engine, and Blender
- 🌐 **In-Browser 3D Preview** - Interactive preview using Google's `<model-viewer>` web component
- ⚡ **Lightweight** - Small dependency footprint; the server starts in seconds and runs comfortably on free-tier hosts
- 🆓 **Completely Free** - No accounts, no API keys, no paid tiers
- 🔓 **Open Source** - MIT licensed, fork and modify as you wish

## 🎯 Use Cases

- **Architecture & Real Estate** - Visualize 2D floor plans as 3D models
- **Education** - Learn about classical computer-vision pipelines and 3D mesh generation
- **Prototyping** - Quickly turn a sketch or CAD-style plan into editable geometry
- **Creative Projects** - Bring drawn layouts into a 3D scene

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/RattusKing/Allspace.git
cd Allspace
```

2. **Set up a Python virtual environment**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start the backend server**
```bash
python app.py
```

The app will be available at `http://localhost:5000`. The Flask backend serves the frontend (`index.html`) directly at `/`, so there is no separate frontend server to run.

### First Generation

1. Open your browser to `http://localhost:5000`
2. Drag and drop a floor plan image or click to browse
3. Adjust the available options (scale, etc.)
4. Click to generate the 3D model
5. Preview your model in the interactive viewer
6. Download the GLB or OBJ file

> Options: **Room complexity** controls the working resolution and how finely walls
> are traced (low = faster/coarser, high = more detail). **Interior elements** toggles
> per-room colour-coded floors. **Scale** sets real-world metre dimensions on the
> exported model (assumes a 96 DPI scan).

## 📁 Project Structure

```
Allspace/
├── index.html                      # Web interface (served by Flask at /)
├── backend/
│   ├── app.py                      # Flask API server + pipeline orchestration
│   ├── requirements.txt            # Python dependencies
│   ├── gunicorn_config.py          # Gunicorn production config
│   ├── test_setup.py               # Setup/sanity check script
│   ├── models/
│   │   ├── __init__.py
│   │   └── depth_estimator.py      # Classical-CV scene classification + wall mask
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── mesh_generator.py       # 3D mesh creation (wall extrusion, floors)
│   │   └── exporter.py             # GLB + OBJ export
│   ├── uploads/                    # Temporary image storage
│   └── outputs/                    # Generated 3D models
├── render.yaml                     # Render deployment blueprint
├── .gitignore
├── LICENSE                         # MIT License
└── README.md
```

## 🔧 How It Works

The whole pipeline is hand-written classical computer vision built on OpenCV, NumPy, SciPy, and trimesh. There is **no machine-learning model** anywhere in it.

### 1. Scene Classification
- `depth_estimator.py` (`_detect_scene_type`) heuristically classifies the uploaded image — floor plan, building facade, indoor room, or generic photo — using brightness, color saturation, and Hough line counts.

### 2. Wall Mask (floor plan path)
- For floor plans, `_floorplan_depth` builds a binary wall mask: the image is resized so the longest side is ~1024px, dark pixels are thresholded (`gray < 120`), morphological closing fills gaps, and connected components are filtered by area. Wall pixels = `1.0`, floor = `0.0`. No depth network is involved.

### 3. Mesh Generation
- `mesh_generator._architectural_mesh` traces the wall mask with `findContours`, simplifies the outlines with `approxPolyDP`, and extrudes each edge into vertical wall quads. It detects door/window openings and builds per-room floor tiles to produce 3D architectural geometry.

### 4. Export
- `exporter.py` writes the mesh to GLB (glTF Binary) for the in-browser viewer and downloads, and to OBJ for desktop 3D tools and game engines.

## 🎮 Import into Other Tools

### Blender
1. Download the GLB file
2. File → Import → glTF 2.0
3. Select your downloaded file
4. The model appears in the scene

### Unity / Unreal Engine
Import the OBJ directly, or use GLB / glTF (Unity via the glTF importer / UnityGLTF; Unreal via the glTF importer or Datasmith). Drag the file into your project's assets and configure import as needed.

## ☁️ Deployment

### Backend - Render

1. **Create a Render account** at [render.com](https://render.com)

2. **Create a new Web Service**
   - Connect your GitHub repository (`Allspace`)
   - Select `backend` as the root directory
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT app:app`

3. **Deploy** - Render will build and deploy automatically. The app is lightweight (no PyTorch, no model downloads), so builds and cold starts are fast.

Because Flask serves `index.html` at `/`, deploying the backend deploys the whole app — frontend included. Open the Render service URL directly to use it.

## 🛠️ API Endpoints

### `GET /`
Serves the web interface (`index.html`).

### `POST /generate`
Run the full pipeline and generate a 3D model.
- **Body**: `multipart/form-data` with:
  - `image` — the floor plan image file (required)
  - `complexity` — `low` | `medium` (default) | `high`; sets working resolution and contour detail
  - `generate_interiors` — `true` (default) | `false`; toggles per-room colour-coded floors
  - `scale` — `auto` (default) or a numeric scale ratio used to compute real-world dimensions for floor plans
- **Returns**: JSON with `job_id` and absolute download URLs (`model_url` / `glb_url` / `obj_url`)

### `GET /api/download/<job_id>/<format>`
Download a generated model.
- **format**: `glb` or `obj`
- **Returns**: the 3D model file

## 🧪 Testing

```bash
# Sanity-check the backend setup
cd backend
python test_setup.py

# Hit the running server
curl http://localhost:5000/
```

## 🐛 Troubleshooting

### "Generation failed" / 500 error
- **Cause**: Unsupported or unexpected image, or an image that misclassifies (e.g. a colored/blue plan handled as a photo).
- **Solution**: Use a clean floor plan with dark walls on a light background. See `FLOORPLAN-DIAGNOSIS.md` for the known accuracy limits of the wall detector.

### "Invalid job_id" on download
- **Cause**: Jobs are tracked in memory and are lost when the server restarts.
- **Solution**: Re-run the generation to get a fresh `job_id`, then download.

### "Out of memory error"
- **Cause**: Very large image.
- **Solution**: Use a smaller image. (Note: inputs are downscaled to ~1024px internally before processing.)

### "File cleanup not working"
- **Cause**: The background cleanup thread may fail on some systems.
- **Solution**: Manually delete old files from `backend/uploads/` and `backend/outputs/`.

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Areas for Contribution

- 🏗️ More robust wall detection (line/centerline geometry, multiple drawing styles)
- 📐 Preserve true aspect ratio and scale from drawn dimensions
- 🚪 Better door/window detection from drawn symbols
- 🚪 Distinguish non-wall symbols (text, dimensions, furniture) from walls
- 📦 Real FBX export (needs an external converter — currently GLB + OBJ only)
- 🧪 More comprehensive test coverage
- 📚 Documentation improvements

See `FLOORPLAN-DIAGNOSIS.md` for a detailed, file-referenced breakdown of current limitations and a remediation roadmap.

## 📝 Technical Details

### Libraries

- **Flask** + **flask-cors** + **Werkzeug** - Web API framework
- **OpenCV** (`opencv-python-headless`) - Image processing and classical computer vision
- **NumPy** / **SciPy** - Numerical and image array operations
- **trimesh** - Mesh construction and GLB export
- **NetworkX** - Graph utilities used during mesh processing
- **Pillow** - Image loading
- **gunicorn** - Production WSGI server
- **Google `<model-viewer>`** - In-browser 3D preview (loaded in `index.html`)

No PyTorch, no MiDaS, no Open3D, no neural networks — the engine is entirely classical CPU computer vision.

## 📊 Limitations

- The wall detector is tuned for dark walls on a clean, light background near one DPI/scale. Blueprints, colored/real-estate plans, gray-filled walls, and photographed plans can break it.
- Walls are traced as blob outlines (not centerlines) with a fixed thickness, which rounds corners and can inflate room sizes.
- Door/window openings are guessed from pixel brightness, so they can be wrong.
- True real-world scale is only approximate, and only when a numeric scale is supplied (it assumes 96 DPI).
- Only GLB and OBJ are exported; there is no real FBX writer (trimesh cannot author FBX).
- `job_id`s are stored in memory and are lost on server restart.

> Aspect-ratio squashing and the aggressive 640px downscale described in earlier
> revisions have been fixed: inputs now process at up to ~1024px and the normalized
> footprint preserves the drawing's true proportions.

(See `FLOORPLAN-DIAGNOSIS.md` for full details and file:line references.)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

You are free to:
- ✅ Use commercially
- ✅ Modify and distribute
- ✅ Use privately
- ✅ Sublicense

The only requirement is to include the original copyright notice.

## 🙏 Acknowledgments

- **OpenCV** - For the computer-vision toolkit this is built on
- **trimesh** - For mesh construction and glTF/GLB export
- **Google `<model-viewer>`** - For making in-browser 3D preview easy
- **Flask** - For a fantastic web framework
- **The open-source community** - For making projects like this possible

## 📧 Contact & Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/RattusKing/Allspace/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/RattusKing/Allspace/discussions)

## ⭐ Star History

If you find this project useful, please consider giving it a star! It helps others discover the project.

---

**Made with ❤️ by the open-source community**

*No accounts, no paywalls, no tracking - just free, open-source floor-plan-to-3D conversion for everyone.*
