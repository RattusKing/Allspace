# 🎨 Image to 3D Environment Generator

Transform any 2D image into a complete, explorable 3D environment with AI-powered depth estimation and procedural generation of unseen areas.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)

## ✨ Features

- 🖼️ **Universal Image Support** - Upload any 2D image: photos, maps, concept art, architectural drawings
- 🤖 **AI Depth Estimation** - Uses MiDaS for accurate monocular depth estimation
- 🎭 **Unseen Area Hallucination** - Procedurally generates rooms, interiors, and structures behind walls
- 📦 **Multiple Export Formats** - Export as GLB and FBX for Unity, Unreal Engine, and Blender
- 🌐 **3D Preview** - Interactive Three.js viewer directly in your browser
- 🆓 **Completely Free** - No accounts, no API keys, no paid tiers
- 🔓 **Open Source** - MIT licensed, fork and modify as you wish

## 🎯 Use Cases

- **Game Development** - Generate 3D environments from concept art
- **Architecture** - Visualize 2D floor plans in 3D
- **Virtual Tours** - Create explorable spaces from photographs
- **Education** - Learn about depth estimation and 3D reconstruction
- **Creative Projects** - Transform art into interactive 3D scenes

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- 4GB+ RAM (8GB+ recommended for larger images)
- MacBook Air or better (tested on M1/M2 Macs)

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/image-to-3d-generator.git
cd image-to-3d-generator
```

2. **Set up Python virtual environment**
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

The API will be available at `http://localhost:5000`

5. **Serve the frontend** (in a new terminal)
```bash
cd frontend
python3 -m http.server 8000
```

The web interface will be available at `http://localhost:8000`

### First Generation

1. Open your browser to `http://localhost:8000`
2. Drag and drop an image or click to browse
3. Configure generation options:
   - **Hallucinate unseen areas** - Generate rooms and interiors
   - **Interior elements** - Add furniture, machinery, etc.
   - **Complexity** - Low (faster) to High (more detail)
   - **Wall thickness** - Adjust wall depth (0.1-1.0 meters)
4. Click "Generate 3D Environment"
5. Wait for processing (typically 30-90 seconds)
6. Preview your 3D model in the interactive viewer
7. Download as GLB or FBX

## 📁 Project Structure

```
image-to-3d-generator/
├── backend/
│   ├── app.py                      # Flask API server
│   ├── requirements.txt            # Python dependencies
│   ├── models/
│   │   ├── __init__.py
│   │   └── depth_estimator.py      # MiDaS depth estimation
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── mesh_generator.py       # 3D mesh creation
│   │   ├── procedural_generator.py # Unseen area hallucination
│   │   └── exporter.py             # GLB/FBX export
│   ├── uploads/                    # Temporary image storage
│   └── outputs/                    # Generated 3D models
├── frontend/
│   ├── index.html                  # Web interface
│   ├── style.css                   # Styling
│   ├── app.js                      # Application logic
│   └── viewer.js                   # Three.js 3D viewer
├── .gitignore
├── LICENSE                         # MIT License
└── README.md
```

## 🔧 How It Works

### 1. Depth Estimation
- Uses Intel's MiDaS model for monocular depth estimation
- Generates a depth map from the input image
- Calculates confidence scores for each pixel

### 2. Base Mesh Generation
- Converts depth map to 3D point cloud
- Applies Poisson surface reconstruction or ball pivoting
- Maps original image colors to vertices

### 3. Procedural Hallucination
- Analyzes scene type (interior, exterior, factory, etc.)
- Generates back walls, side walls, floors, and ceilings
- Adds interior elements based on scene type:
  - **Factories** - Catwalks, pipes, machinery
  - **Interiors** - Furniture, fixtures
  - **Buildings** - Structural elements, pillars

### 4. Export
- Converts to trimesh format
- Exports to GLB (glTF Binary) for web use
- Exports to FBX for game engines and 3D software

## 🎮 Import into Game Engines

### Unity
1. Download the FBX file
2. Drag into Unity's Assets folder
3. The model will be automatically imported with materials

### Unreal Engine
1. Download the FBX file
2. In Content Browser, click Import
3. Select the FBX file and configure import settings
4. Materials and textures will be imported

### Blender
1. Download either GLB or FBX
2. File → Import → FBX (or glTF 2.0)
3. Select your downloaded file
4. Model appears in the scene

## ☁️ Deployment

### Backend - Render

1. **Create a Render account** at [render.com](https://render.com)

2. **Create a new Web Service**
   - Connect your GitHub repository
   - Select `backend` as the root directory
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

3. **Add environment variables** (if needed)

4. **Deploy** - Render will build and deploy automatically

5. **Update frontend API URL**
   - Edit `frontend/app.js`
   - Change `API_URL` to your Render URL

### Frontend - GitHub Pages

1. **Enable GitHub Pages**
   - Go to repository Settings → Pages
   - Source: Deploy from a branch
   - Branch: main, folder: /frontend
   - Save

2. **Access your site**
   - Your site will be available at: `https://yourusername.github.io/image-to-3d-generator/`

3. **Configure CORS**
   - Ensure your Render backend allows requests from your GitHub Pages domain

## 🛠️ API Endpoints

### `GET /`
Health check and API information

### `POST /api/upload`
Upload an image for processing
- **Body**: multipart/form-data with `image` file
- **Returns**: `job_id` for tracking

### `POST /api/generate`
Start 3D generation
- **Body**: JSON with `job_id` and options
- **Returns**: Generation status

### `GET /api/status/:job_id`
Check generation status
- **Returns**: Progress, status, and output files

### `GET /api/download/:job_id/:format`
Download generated model
- **format**: `glb` or `fbx`
- **Returns**: 3D model file

## 🧪 Testing

```bash
# Run backend tests
cd backend
pytest

# Test API endpoints
curl http://localhost:5000/
```

## 🐛 Troubleshooting

### "Model download failed"
- **Cause**: First run downloads MiDaS models (~100MB)
- **Solution**: Wait for download to complete, check internet connection

### "Generation stuck at 0%"
- **Cause**: Backend not running or wrong API URL
- **Solution**: Verify backend is running at the URL specified in `frontend/app.js`

### "Out of memory error"
- **Cause**: Image too large or system RAM insufficient
- **Solution**: Resize image to max 2000px, close other applications

### "FBX export failed"
- **Cause**: pyassimp not installed or unavailable
- **Solution**: Model exports as OBJ instead (fallback), or install pyassimp

### "File cleanup not working"
- **Cause**: Cleanup thread may fail on some systems
- **Solution**: Manually delete old files from `uploads/` and `outputs/` folders

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Areas for Contribution

- 🎨 Better procedural generation algorithms
- 🤖 Support for additional depth estimation models
- 🎮 Unity/Unreal plugins for direct import
- 🌐 Multi-language support
- 📱 Mobile-responsive design improvements
- 🧪 More comprehensive test coverage
- 📚 Documentation improvements

## 📝 Technical Details

### AI Models

**MiDaS (Monocular Depth Estimation)**
- Paper: [Towards Robust Monocular Depth Estimation](https://arxiv.org/abs/1907.01341)
- Model: Intel ISL (Intelligent Systems Lab)
- Uses: Depth map generation from single images
- Performance: ~2-5 seconds per image on CPU

### Libraries

- **Flask** - Web API framework
- **Open3D** - 3D data processing
- **trimesh** - Mesh manipulation and export
- **PyTorch** - Deep learning inference
- **Three.js** - WebGL 3D visualization

### Performance

- **Small images (512x512)**: ~30 seconds
- **Medium images (1024x1024)**: ~60 seconds
- **Large images (2048x2048)**: ~90 seconds

Times vary based on:
- Image size
- Complexity settings
- System specifications
- CPU vs GPU availability

## 📊 Limitations

- Depth estimation works best with images that have clear perspective
- Flat/abstract art may produce unexpected results (but can be interesting!)
- Very large images (>4K) may require significant processing time
- Procedural generation is rule-based, not AI-powered (yet!)
- FBX export requires additional system libraries on some platforms

## 🔮 Future Enhancements

- [ ] GPU acceleration for faster processing
- [ ] Support for Depth Anything and other depth models
- [ ] AI-powered interior element generation
- [ ] Texture synthesis for unseen areas
- [ ] Batch processing multiple images
- [ ] Progressive web app (PWA) support
- [ ] Advanced mesh optimization options
- [ ] Custom procedural generation rules
- [ ] Real-time preview during generation
- [ ] Video to 3D environment (frame-by-frame)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

You are free to:
- ✅ Use commercially
- ✅ Modify and distribute
- ✅ Use privately
- ✅ Sublicense

The only requirement is to include the original copyright notice.

## 🙏 Acknowledgments

- **Intel ISL** - For the MiDaS depth estimation model
- **Open3D** - For excellent 3D processing capabilities
- **Three.js** - For making WebGL accessible
- **Flask** - For a fantastic web framework
- **The open-source community** - For making projects like this possible

## 📧 Contact & Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/image-to-3d-generator/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/image-to-3d-generator/discussions)
- 📖 **Wiki**: [Project Wiki](https://github.com/yourusername/image-to-3d-generator/wiki)

## ⭐ Star History

If you find this project useful, please consider giving it a star! It helps others discover the project.

---

**Made with ❤️ by the open-source community**

*No accounts, no paywalls, no tracking - just free, open-source 3D generation for everyone.*
