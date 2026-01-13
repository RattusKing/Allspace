#!/bin/bash

# Quick start script for Image to 3D Generator

echo "🎨 Image to 3D Environment Generator"
echo "===================================="
echo ""

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "📦 Creating virtual environment..."
    cd backend
    python3 -m venv venv
    cd ..
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source backend/venv/bin/activate

# Check if dependencies are installed
if ! python -c "import flask" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    cd backend
    pip install -r requirements.txt
    cd ..
fi

# Start the backend
echo ""
echo "🚀 Starting backend server..."
echo "   API will be available at: http://localhost:5000"
echo ""
echo "💡 In another terminal, run:"
echo "   cd frontend && python3 -m http.server 8000"
echo "   Then open: http://localhost:8000"
echo ""

cd backend
python app.py
