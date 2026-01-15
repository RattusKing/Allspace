/**
 * Image to 3D Environment Generator - Frontend Application
 * Handles file uploads, API communication, and UI state management
 */

// Configuration
const API_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:5000'
    : 'https://allspace.onrender.com';

// State
let currentJobId = null;
let currentFile = null;
let statusCheckInterval = null;

// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const previewSection = document.getElementById('previewSection');
const previewImg = document.getElementById('previewImg');
const fileName = document.getElementById('fileName');
const changeImageBtn = document.getElementById('changeImageBtn');
const optionsSection = document.getElementById('optionsSection');
const generateBtn = document.getElementById('generateBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const progressPercent = document.getElementById('progressPercent');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');
const downloadGlbBtn = document.getElementById('downloadGlbBtn');
const downloadFbxBtn = document.getElementById('downloadFbxBtn');
const startOverBtn = document.getElementById('startOverBtn');
const retryBtn = document.getElementById('retryBtn');
const wallThicknessSlider = document.getElementById('wallThicknessSlider');
const wallThicknessValue = document.getElementById('wallThicknessValue');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    console.log('🚀 Image to 3D Generator initialized');
    console.log(`📡 API URL: ${API_URL}`);
});

function initializeEventListeners() {
    // File upload events
    uploadBox.addEventListener('click', () => fileInput.click());
    uploadBox.addEventListener('dragover', handleDragOver);
    uploadBox.addEventListener('dragleave', handleDragLeave);
    uploadBox.addEventListener('drop', handleDrop);
    fileInput.addEventListener('change', handleFileSelect);
    browseBtn.addEventListener('click', () => fileInput.click());

    // Action buttons
    changeImageBtn.addEventListener('click', resetToUpload);
    generateBtn.addEventListener('click', handleGenerate);
    startOverBtn.addEventListener('click', resetToUpload);
    retryBtn.addEventListener('click', resetToUpload);

    // Download buttons
    downloadGlbBtn.addEventListener('click', () => downloadModel('glb'));
    downloadFbxBtn.addEventListener('click', () => downloadModel('fbx'));

    // Options
    wallThicknessSlider.addEventListener('input', (e) => {
        wallThicknessValue.textContent = e.target.value;
    });
}

// Drag and Drop Handlers
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadBox.style.borderColor = 'var(--primary-color)';
    uploadBox.style.background = 'var(--surface-light)';
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadBox.style.borderColor = 'var(--border-color)';
    uploadBox.style.background = 'var(--bg-color)';
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadBox.style.borderColor = 'var(--border-color)';
    uploadBox.style.background = 'var(--bg-color)';

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

// File Processing
function processFile(file) {
    // Validate file type
    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/tiff'];
    if (!validTypes.includes(file.type)) {
        showError('Invalid file type. Please upload a JPG, PNG, WEBP, BMP, or TIFF image.');
        return;
    }

    // Validate file size (16MB)
    const maxSize = 16 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('File too large. Maximum size is 16MB.');
        return;
    }

    currentFile = file;

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        fileName.textContent = file.name;
        showSection('preview');
    };
    reader.readAsDataURL(file);
}

// API Communication
async function uploadImage() {
    if (!currentFile) {
        showError('No file selected');
        return null;
    }

    try {
        const formData = new FormData();
        formData.append('image', currentFile);

        const response = await fetch(`${API_URL}/api/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Upload failed');
        }

        const data = await response.json();
        return data.job_id;

    } catch (error) {
        console.error('Upload error:', error);
        throw error;
    }
}

async function startGeneration(jobId) {
    try {
        // Get options
        const options = {
            job_id: jobId,
            hallucinate_unseen: document.getElementById('hallucinateCheckbox').checked,
            generate_interiors: document.getElementById('interiorsCheckbox').checked,
            room_complexity: document.getElementById('complexitySelect').value,
            wall_thickness: parseFloat(wallThicknessSlider.value)
        };

        const response = await fetch(`${API_URL}/api/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(options)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Generation failed');
        }

        const data = await response.json();
        return data;

    } catch (error) {
        console.error('Generation error:', error);
        throw error;
    }
}

async function checkStatus(jobId) {
    try {
        const response = await fetch(`${API_URL}/api/status/${jobId}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Status check failed');
        }

        const data = await response.json();
        return data;

    } catch (error) {
        console.error('Status check error:', error);
        throw error;
    }
}

// Generation Handler
async function handleGenerate() {
    try {
        showSection('progress');
        updateProgress(0, 'Uploading image...');

        // Step 1: Upload image
        const jobId = await uploadImage();
        if (!jobId) {
            throw new Error('Failed to get job ID');
        }

        currentJobId = jobId;
        console.log(`✅ Image uploaded, job ID: ${jobId}`);

        updateProgress(10, 'Starting generation...');

        // Step 2: Start generation
        await startGeneration(jobId);

        // Step 3: Poll for status
        statusCheckInterval = setInterval(async () => {
            try {
                const status = await checkStatus(jobId);

                updateProgress(status.progress, status.current_step || 'Processing...');

                if (status.status === 'completed') {
                    clearInterval(statusCheckInterval);
                    handleGenerationComplete(status);
                } else if (status.status === 'failed') {
                    clearInterval(statusCheckInterval);
                    throw new Error(status.error || 'Generation failed');
                }

            } catch (error) {
                clearInterval(statusCheckInterval);
                showError(error.message);
            }
        }, 2000); // Check every 2 seconds

    } catch (error) {
        console.error('Generation error:', error);
        showError(error.message || 'Generation failed. Please try again.');
    }
}

function handleGenerationComplete(status) {
    console.log('✅ Generation complete:', status);
    updateProgress(100, 'Complete!');

    // Show results after a brief delay
    setTimeout(() => {
        showSection('results');

        // Load 3D preview
        if (status.output_files && status.output_files.glb) {
            const glbUrl = `${API_URL}/api/download/${currentJobId}/glb`;
            loadModel(glbUrl);
        }
    }, 500);
}

// Download Handler
function downloadModel(format) {
    if (!currentJobId) {
        showError('No model available for download');
        return;
    }

    const downloadUrl = `${API_URL}/api/download/${currentJobId}/${format}`;
    console.log(`📥 Downloading ${format.toUpperCase()}: ${downloadUrl}`);

    // Create temporary link and trigger download
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `generated_3d_environment.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// UI State Management
function showSection(section) {
    // Hide all sections
    document.getElementById('uploadSection').classList.add('hidden');
    previewSection.classList.add('hidden');
    optionsSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');

    // Show appropriate sections
    switch (section) {
        case 'upload':
            document.getElementById('uploadSection').classList.remove('hidden');
            break;
        case 'preview':
            document.getElementById('uploadSection').classList.add('hidden');
            previewSection.classList.remove('hidden');
            optionsSection.classList.remove('hidden');
            break;
        case 'progress':
            progressSection.classList.remove('hidden');
            break;
        case 'results':
            resultsSection.classList.remove('hidden');
            break;
        case 'error':
            errorSection.classList.remove('hidden');
            break;
    }
}

function updateProgress(percent, text) {
    progressFill.style.width = `${percent}%`;
    progressPercent.textContent = `${Math.round(percent)}%`;
    progressText.textContent = text;
}

function showError(message) {
    errorMessage.textContent = message;
    showSection('error');
}

function resetToUpload() {
    // Clear state
    currentJobId = null;
    currentFile = null;
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }

    // Reset form
    fileInput.value = '';
    previewImg.src = '';

    // Reset 3D viewer
    if (window.viewer) {
        window.viewer.dispose();
    }

    // Show upload section
    showSection('upload');
}

// Utility Functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Test API connection on load
async function testApiConnection() {
    try {
        const response = await fetch(`${API_URL}/`);
        const data = await response.json();
        console.log('✅ API connection successful:', data);
    } catch (error) {
        console.error('❌ API connection failed:', error);
        console.log('⚠️  Make sure the backend is running!');
    }
}

// Test connection
testApiConnection();
