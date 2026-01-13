# 🚀 Deployment Guide

This guide will help you deploy the Image to 3D Generator so it's fully working on GitHub Pages.

## Architecture

```
User Browser → GitHub Pages (Frontend) → Render API (Backend) → Returns 3D Model
```

- **Frontend**: Hosted on GitHub Pages (FREE, static hosting)
- **Backend**: Hosted on Render (FREE tier available)

## Step 1: Deploy Backend to Render (5 minutes)

1. **Create Render Account**
   - Go to https://render.com
   - Sign up with GitHub (recommended)

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository: `Allspace`

3. **Configure the Service**
   - **Name**: `image-to-3d-api` (or your choice)
   - **Region**: Choose closest to you
   - **Branch**: `claude/2d-to-3d-environment-l0rm5`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -c gunicorn_config.py app:app`
   - **Instance Type**: `Free` (sufficient for testing)

4. **Deploy**
   - Click "Create Web Service"
   - Wait 5-10 minutes for initial deployment
   - Note your API URL: `https://image-to-3d-api-xxxx.onrender.com`

5. **Test Backend**
   - Visit your URL in browser
   - You should see: `{"status": "online", "service": "Image to 3D Environment Generator", ...}`

## Step 2: Update Frontend to Use Deployed Backend

Update `frontend/app.js` with your Render URL:

```javascript
const API_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:5000'
    : 'https://YOUR-RENDER-URL.onrender.com';  // ← Change this!
```

## Step 3: Deploy Frontend to GitHub Pages (2 minutes)

### Option A: Using GitHub Settings (Easiest)

1. **Push Changes**
   ```bash
   git add frontend/app.js
   git commit -m "Update API URL for production"
   git push
   ```

2. **Enable GitHub Pages**
   - Go to your repo on GitHub
   - Settings → Pages
   - Source: "Deploy from a branch"
   - Branch: `claude/2d-to-3d-environment-l0rm5`
   - Folder: `/ (root)` or `/frontend` depending on your setup
   - Click "Save"

3. **Wait 1-2 minutes**
   - Your site will be live at: `https://rattusking.github.io/Allspace/`
   - If using `/frontend` folder, adjust the path accordingly

### Option B: Custom Deployment

Create `frontend/.nojekyll` file to prevent GitHub from processing files:

```bash
touch frontend/.nojekyll
git add frontend/.nojekyll
git commit -m "Add .nojekyll for GitHub Pages"
git push
```

## Step 4: Test the Full Application

1. Visit your GitHub Pages URL
2. Upload an image
3. Configure options
4. Click "Generate 3D Environment"
5. Wait for processing
6. Download your 3D model!

## Important: CORS Configuration

The backend is already configured with Flask-CORS to accept requests from any origin. If you encounter CORS issues:

1. Check Render logs for errors
2. Verify the API URL in `frontend/app.js` is correct
3. Ensure Render service is running

## Troubleshooting

### "Failed to fetch" Error
- **Cause**: Backend not running or wrong URL
- **Solution**: Check Render dashboard, verify service is "Live"

### GitHub Pages 404
- **Cause**: Path configuration issue
- **Solution**: 
  - Make sure `index.html` is in the root or `/frontend`
  - Check Pages settings for correct folder

### Render "Out of Memory"
- **Cause**: Free tier limitations
- **Solution**: 
  - Use smaller images
  - Upgrade to paid tier ($7/month)

### First Generation Slow
- **Cause**: MiDaS model downloads on first use (~100MB)
- **Solution**: Wait for initial download, subsequent requests are faster

### Backend Goes to Sleep
- **Cause**: Render free tier spins down after 15 min inactivity
- **Solution**: 
  - First request may take 30-60 seconds to wake up
  - Upgrade to paid tier for always-on service

## Costs

- **GitHub Pages**: 100% FREE forever
- **Render Free Tier**: 
  - ✅ FREE for 750 hours/month
  - ✅ Sufficient for personal projects
  - ⚠️ Spins down after 15 min inactivity
  - ⚠️ 512MB RAM (may limit large images)

- **Render Paid Tier** ($7/month):
  - ✅ Always on
  - ✅ More RAM (2GB+)
  - ✅ Faster processing

## Monitoring

Check Render Dashboard:
- View logs for errors
- Monitor resource usage
- See request history

## Updates

To update the application:

1. Make changes locally
2. Test locally
3. Commit and push
4. Render auto-deploys backend
5. GitHub Pages auto-deploys frontend

## Alternative Backends

If Render doesn't work for you:

- **Railway.app**: Similar to Render, generous free tier
- **Fly.io**: Good free tier, multiple regions
- **PythonAnywhere**: Python-specific hosting
- **AWS Lambda**: Serverless option (requires changes)

## Security Notes

- API is public (anyone can use it)
- Consider adding rate limiting for production
- Monitor Render usage to avoid abuse
- Files auto-delete after 24 hours

## Next Steps

1. Deploy backend to Render
2. Update frontend API URL
3. Deploy frontend to GitHub Pages
4. Share your live URL!
5. Consider custom domain (optional)

---

**Your Live App**: `https://rattusking.github.io/Allspace/` → `https://your-api.onrender.com`

Completely free, completely working, completely open-source! 🎉
