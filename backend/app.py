"""
Image to 3D Environment Generator - Flask Backend API
Converts 2D images into explorable 3D environments with procedurally generated unseen areas
"""

import os
import uuid
import shutil
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading
import time

# Import our custom modules
from models.depth_estimator import DepthEstimator
from utils.mesh_generator import MeshGenerator
from utils.procedural_generator import ProceduralGenerator
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

# Initialize AI models and generators
depth_estimator = DepthEstimator()
mesh_generator = MeshGenerator()
procedural_generator = ProceduralGenerator()
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
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'Image to 3D Environment Generator',
        'version': '1.0.0',
        'endpoints': {
            'upload': '/api/upload',
            'generate': '/api/generate',
            'status': '/api/status/<job_id>',
            'download': '/api/download/<job_id>/<format>'
        }
    })


@app.route('/api/upload', methods=['POST'])
def upload_image():
    """
    Upload an image for 3D conversion
    Returns: job_id for tracking the upload
    """
    try:
        # Check if file is in request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']

        # Check if filename is empty
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Save file with job_id
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        save_filename = f"{job_id}.{file_ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], save_filename)
        file.save(filepath)

        # Store job information
        generation_jobs[job_id] = {
            'status': 'uploaded',
            'filename': save_filename,
            'original_filename': filename,
            'created_at': datetime.now().isoformat(),
            'progress': 0
        }

        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Image uploaded successfully'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@app.route('/api/generate', methods=['POST'])
def generate_3d():
    """
    Generate 3D environment from uploaded image
    Expects: job_id and optional parameters
    """
    try:
        data = request.get_json()

        if not data or 'job_id' not in data:
            return jsonify({'error': 'job_id is required'}), 400

        job_id = data['job_id']

        # Validate job exists
        if job_id not in generation_jobs:
            return jsonify({'error': 'Invalid job_id'}), 404

        job = generation_jobs[job_id]

        if job['status'] != 'uploaded':
            return jsonify({'error': f'Job already {job["status"]}'}), 400

        # Get optional parameters
        options = {
            'hallucinate_unseen': data.get('hallucinate_unseen', True),
            'room_complexity': data.get('room_complexity', 'medium'),  # low, medium, high
            'wall_thickness': data.get('wall_thickness', 0.3),
            'generate_interiors': data.get('generate_interiors', True)
        }

        # Start generation in background thread
        def generate_async():
            try:
                job['status'] = 'processing'
                job['progress'] = 10

                # Load image
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], job['filename'])

                # Step 1: Generate depth map
                job['progress'] = 20
                job['current_step'] = 'Estimating depth'
                depth_map, confidence_map = depth_estimator.estimate_depth(image_path)

                # Step 2: Create base 3D mesh from image and depth
                job['progress'] = 40
                job['current_step'] = 'Generating base mesh'
                base_mesh, image_data = mesh_generator.create_mesh_from_depth(
                    image_path, depth_map, confidence_map
                )

                # Step 3: Procedurally generate unseen areas
                if options['hallucinate_unseen']:
                    job['progress'] = 60
                    job['current_step'] = 'Hallucinating unseen areas'
                    enhanced_mesh = procedural_generator.generate_unseen_geometry(
                        base_mesh,
                        image_data,
                        depth_map,
                        options
                    )
                else:
                    enhanced_mesh = base_mesh

                # Step 4: Export to different formats
                job['progress'] = 80
                job['current_step'] = 'Exporting models'

                output_files = {}

                # Export GLB
                glb_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}.glb")
                model_exporter.export_glb(enhanced_mesh, glb_path, image_data)
                output_files['glb'] = f"{job_id}.glb"

                # Export FBX
                fbx_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}.fbx")
                model_exporter.export_fbx(enhanced_mesh, fbx_path, image_data)
                output_files['fbx'] = f"{job_id}.fbx"

                # Update job status
                job['progress'] = 100
                job['status'] = 'completed'
                job['current_step'] = 'Complete'
                job['output_files'] = output_files
                job['completed_at'] = datetime.now().isoformat()

            except Exception as e:
                job['status'] = 'failed'
                job['error'] = str(e)
                job['progress'] = 0
                print(f"Generation failed for job {job_id}: {str(e)}")

        # Start async generation
        thread = threading.Thread(target=generate_async)
        thread.start()

        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Generation started',
            'status': 'processing'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Generation failed: {str(e)}'}), 500


@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get the status of a generation job"""
    if job_id not in generation_jobs:
        return jsonify({'error': 'Invalid job_id'}), 404

    job = generation_jobs[job_id]

    response = {
        'job_id': job_id,
        'status': job['status'],
        'progress': job.get('progress', 0),
        'current_step': job.get('current_step', ''),
        'created_at': job['created_at']
    }

    if job['status'] == 'completed':
        response['output_files'] = job.get('output_files', {})
        response['completed_at'] = job.get('completed_at')
    elif job['status'] == 'failed':
        response['error'] = job.get('error', 'Unknown error')

    return jsonify(response), 200


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
