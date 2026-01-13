#!/bin/bash

# Deployment Configuration Script
# Helps set up the frontend to connect to your deployed backend

echo "🚀 Image to 3D Generator - Deployment Configuration"
echo "===================================================="
echo ""

# Get Render URL from user
echo "📝 Enter your Render backend URL"
echo "   (e.g., https://image-to-3d-api-xxxx.onrender.com)"
echo "   Press Enter to skip and use localhost for now"
echo ""
read -p "Render URL: " RENDER_URL

if [ -z "$RENDER_URL" ]; then
    echo "⚠️  No URL provided - frontend will use localhost:5000"
    echo "   You can update this later in frontend/app.js"
else
    # Remove trailing slash if present
    RENDER_URL=${RENDER_URL%/}
    
    echo ""
    echo "📝 Updating frontend/app.js..."
    
    # Update the API URL in app.js
    sed -i.bak "s|https://your-backend-url.onrender.com|${RENDER_URL}|g" frontend/app.js
    
    echo "✅ Updated! Frontend will now use: ${RENDER_URL}"
    
    # Show the change
    echo ""
    echo "Configuration:"
    grep -A 2 "const API_URL" frontend/app.js | head -3
fi

echo ""
echo "===================================================="
echo "📋 Next Steps:"
echo ""
echo "1. Deploy Backend to Render:"
echo "   - Go to https://render.com"
echo "   - Create Web Service from your GitHub repo"
echo "   - Use 'backend' as root directory"
echo "   - Start command: gunicorn -c gunicorn_config.py app:app"
echo ""
echo "2. Get your Render URL and run this script again"
echo ""
echo "3. Enable GitHub Pages:"
echo "   - Go to repo Settings → Pages"
echo "   - Select branch: claude/2d-to-3d-environment-l0rm5"
echo "   - Folder: / (root)"
echo "   - Your site will be at:"
echo "     https://rattusking.github.io/Allspace/"
echo ""
echo "4. Test your deployed application!"
echo "===================================================="
