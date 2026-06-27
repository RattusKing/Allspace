# ⚡ Quick Start - GitHub Pages Deployment

Get Allspace (Floor Plan to 3D Model Converter) live in 10 minutes!

## What You're Deploying

- **Live Website**: `https://rattusking.github.io/Allspace/frontend/`
- **Working Application**: Upload images, generate 3D models, download them
- **100% Free**: No costs, no limits for normal use

## Step 1: Deploy Backend (5 minutes)

### 1.1 Sign up for Render

Go to https://render.com and sign up with GitHub (easiest)

### 1.2 Create Web Service

1. Click "New +" button → "Web Service"
2. Connect to GitHub → Select `RattusKing/Allspace`
3. Fill in the form:

```
Name: image-to-3d-api
Region: Oregon (or closest to you)
Branch: claude/2d-to-3d-environment-l0rm5
Root Directory: backend
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn -c gunicorn_config.py app:app
Instance Type: Free
```

4. Click "Create Web Service"
5. Wait 5-10 minutes for deployment

### 1.3 Get Your API URL

Once deployed, copy your URL:
```
https://image-to-3d-api-xxxx.onrender.com
```

### 1.4 Test Backend

Visit your URL in a browser. You should see the Allspace web interface — Flask serves `index.html` at `/`.

✅ Backend is live!

## Step 2: Configure Frontend (2 minutes)

### 2.1 Update API URL

Run the configuration script:
```bash
./configure-deployment.sh
```

Or manually edit `frontend/app.js` line 7:
```javascript
const API_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:5000'
    : 'https://YOUR-ACTUAL-URL.onrender.com';  // ← Paste your URL here
```

### 2.2 Commit Changes

```bash
git add frontend/app.js frontend/index.html .nojekyll DEPLOYMENT.md QUICKSTART.md configure-deployment.sh
git commit -m "Configure for GitHub Pages deployment"
git push
```

## Step 3: Enable GitHub Pages (1 minute)

1. Go to https://github.com/RattusKing/Allspace
2. Click "Settings" tab
3. Click "Pages" in left sidebar
4. Configure:
   - **Source**: Deploy from a branch
   - **Branch**: `claude/2d-to-3d-environment-l0rm5`
   - **Folder**: `/ (root)`
5. Click "Save"
6. Wait 1-2 minutes

## Step 4: Visit Your Live Site!

Your application is now live at:
```
https://rattusking.github.io/Allspace/frontend/
```

## Testing It Works

1. Visit the URL above
2. Drag and drop an image (or use the browse button)
3. Click "Generate 3D model"
4. Wait 30-90 seconds
5. See your 3D model in the preview!
6. Download as GLB or OBJ

## Troubleshooting

### "Failed to fetch" when generating
- **Cause**: Backend URL not configured or backend is sleeping
- **Fix**: 
  1. Check `frontend/app.js` has correct Render URL
  2. Visit your Render URL directly to wake it up
  3. Try generating again

### GitHub Pages shows 404
- **Cause**: Wrong path or not deployed yet
- **Fix**:
  1. Wait 2-3 minutes for GitHub to build
  2. Try: `https://rattusking.github.io/Allspace/`
  3. Try: `https://rattusking.github.io/Allspace/frontend/`
  4. Check Settings → Pages for the exact URL

### First request takes a while after idle
- **Cause**: On Render's free tier the backend sleeps after ~15 min of inactivity and has to wake up. There is no AI model and no model download — generation is pure CPU OpenCV.
- **Fix**: Just wait a few seconds for it to wake; subsequent requests are immediate.

### Backend returns 500 error
- **Cause**: An unsupported or misclassified image (e.g. a colored plan handled as a photo), or low memory on a very large image.
- **Fix**: Use a clean floor plan with dark walls on a light background; try a smaller image. Check Render logs for details.

## Sharing Your Project

Your live link:
```
https://rattusking.github.io/Allspace/frontend/
```

Share on:
- Twitter/X
- Reddit (r/gamedev, r/webdev, r/3Dmodeling)
- Hacker News
- Your portfolio

## Monitoring Usage

**Render Dashboard**: 
- View logs
- See requests
- Monitor uptime

**Free Tier Limits**:
- 750 hours/month (plenty!)
- Sleeps after 15 min inactivity
- 512MB RAM

## Next Steps

1. ✅ Backend deployed to Render
2. ✅ Frontend on GitHub Pages
3. ✅ Working live application
4. 🎉 Share with the world!

Optional:
- Add custom domain
- Upgrade Render for always-on
- Add analytics
- Accept contributions

---

**That's it! Your free, open-source Image to 3D Generator is now live! 🚀**
