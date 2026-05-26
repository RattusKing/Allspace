"""
Allspace — Floor Plan to 3D Model Converter
Flask backend API
"""

import os
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading
import time

from models.depth_estimator import DepthEstimator
from utils.mesh_generator import MeshGenerator
from utils.exporter import ModelExporter

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
CLEANUP_INTERVAL = 3600  # Cleanup every hour
FILE_RETENTION_HOURS = 24

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

depth_estimator = DepthEstimator()
mesh_generator = MeshGenerator()
model_exporter = ModelExporter()

# Store for tracking generation jobs
generation_jobs = {}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_old_files():
    """Remove files older than FILE_RETENTION_HOURS"""
    while True:
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=FILE_RETENTION_HOURS)

            # Cleanup uploads
            for filename in os.listdir(UPLOAD_FOLDER):
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.isfile(filepath):
                    file_modified = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_modified < cutoff_time:
                        os.remove(filepath)
                        print(f"Cleaned up old upload: {filename}")

            # Cleanup outputs
            for filename in os.listdir(OUTPUT_FOLDER):
                filepath = os.path.join(OUTPUT_FOLDER, filename)
                if os.path.isfile(filepath):
                    file_modified = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_modified < cutoff_time:
                        os.remove(filepath)
                        print(f"Cleaned up old output: {filename}")

            # Cleanup old jobs from memory
            jobs_to_remove = []
            for job_id, job_data in generation_jobs.items():
                if job_data.get('created_at'):
                    job_time = datetime.fromisoformat(job_data['created_at'])
                    if job_time < cutoff_time:
                        jobs_to_remove.append(job_id)

            for job_id in jobs_to_remove:
                del generation_jobs[job_id]
                print(f"Cleaned up old job: {job_id}")

        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

        time.sleep(CLEANUP_INTERVAL)


# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'status': 'online',
        'service': 'Allspace — Floor Plan to 3D Model Converter',
        'version': '2.0.0',
        'endpoints': {
            'generate': '/generate',
            'download': '/api/download/<job_id>/<format>'
        }
    })


@app.route('/api/download/<job_id>/<format>', methods=['GET'])
def download_model(job_id, format):
    """
    Download generated 3D model
    format: 'glb' or 'fbx'
    """
    try:
        # Validate job
        if job_id not in generation_jobs:
            return jsonify({'error': 'Invalid job_id'}), 404

        job = generation_jobs[job_id]

        if job['status'] != 'completed':
            return jsonify({'error': f'Job is {job["status"]}, not completed'}), 400

        # Validate format
        if format.lower() not in ['glb', 'fbx']:
            return jsonify({'error': 'Invalid format. Use glb or fbx'}), 400

        # Get file path
        filename = job['output_files'].get(format.lower())
        if not filename:
            return jsonify({'error': f'Format {format} not available'}), 404

        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)

        if not os.path.exists(filepath):
            print(f"  ❌ File not found: {filepath}")
            return jsonify({'error': 'File not found'}), 404

        # Check file size
        file_size = os.path.getsize(filepath)
        print(f"  📥 Downloading {format.upper()}: {filepath} ({file_size} bytes)")

        # Determine MIME type
        mime_type = 'model/gltf-binary' if format.lower() == 'glb' else 'application/octet-stream'

        # Send file with proper chunking for large files
        return send_file(
            filepath,
            mimetype=mime_type,
            as_attachment=True,
            download_name=f"generated_3d_environment.{format.lower()}",
            conditional=False,  # Disable conditional responses
            etag=False  # Disable etag caching
        )

    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


@app.route('/generate', methods=['POST'])
def generate_combined():
    """
    Single-step generate endpoint for the redesigned UI.
    Accepts multipart FormData, runs the full pipeline synchronously,
    and returns absolute download URLs.
    """
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400

        job_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        save_filename = f"{job_id}.{file_ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], save_filename)
        file.save(filepath)

        options = {
            'room_complexity': request.form.get('complexity', 'medium'),
            'wall_thickness': 0.3,
            'generate_interiors': request.form.get('generate_interiors', 'true').lower() == 'true',
            'floor_plan_scale': request.form.get('scale', 'auto'),
        }

        depth_map, confidence_map, scene_type = depth_estimator.estimate_depth(filepath)

        from PIL import Image as _PIL_Image
        with _PIL_Image.open(filepath) as _pil_im:
            img_px_w, img_px_h = _pil_im.size

        scale_str = options['floor_plan_scale']
        if scale_str != 'auto' and scene_type == 'floor_plan':
            scale_ratio = float(scale_str)
            dpi = 96.0
            real_width_m  = (img_px_w / dpi * 25.4) * scale_ratio / 1000.0
            real_height_m = (img_px_h / dpi * 25.4) * scale_ratio / 1000.0
            scale_factor_x = real_width_m  / 2.0
            scale_factor_z = real_height_m / 2.0
        else:
            scale_factor_x = 1.0
            scale_factor_z = 1.0

        base_mesh, image_data = mesh_generator.create_mesh_from_depth(
            filepath, depth_map, confidence_map, scene_type=scene_type,
            scale_factor_x=scale_factor_x, scale_factor_z=scale_factor_z
        )

        glb_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}.glb")
        model_exporter.export_glb(base_mesh, glb_path, image_data)

        fbx_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}.fbx")
        model_exporter.export_fbx(base_mesh, fbx_path, image_data)

        generation_jobs[job_id] = {
            'status': 'completed',
            'filename': save_filename,
            'original_filename': filename,
            'created_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat(),
            'progress': 100,
            'output_files': {'glb': f"{job_id}.glb", 'fbx': f"{job_id}.fbx"}
        }

        base_url = request.host_url.rstrip('/')
        glb_url = f"{base_url}/api/download/{job_id}/glb"
        fbx_url = f"{base_url}/api/download/{job_id}/fbx"

        return jsonify({
            'success': True,
            'job_id': job_id,
            'model_url': glb_url,
            'glb_url': glb_url,
            'fbx_url': fbx_url,
        }), 200

    except Exception as e:
        print(f"Combined generate failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413


@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors"""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    print("🚀 Starting Image to 3D Environment Generator API")
    print(f"📁 Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"📁 Output folder: {os.path.abspath(OUTPUT_FOLDER)}")
    print(f"🤖 AI models loaded and ready")
    print(f"🌐 API running on http://0.0.0.0:5000")

    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
