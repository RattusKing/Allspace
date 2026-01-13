# 🌐 Web-Only Setup Guide
## Deploy Without Using Terminal - Only Websites!

Everything can be done through your web browser. No command line needed!

---

## Step 1: Deploy Backend to Render (5 minutes)

### 1.1 Sign Up for Render
1. Go to: **https://render.com**
2. Click **"Get Started"** or **"Sign Up"**
3. Choose **"Sign up with GitHub"** (easiest option)
4. Authorize Render to access your GitHub

### 1.2 Create New Web Service
1. Click the **"New +"** button (top right)
2. Select **"Web Service"**
3. Find and click **"RattusKing/Allspace"** in the list
   - If you don't see it, click "Configure account" to grant access
4. Click **"Connect"** next to the repository

### 1.3 Configure Service
Fill in these settings:

| Setting | Value |
|---------|-------|
| **Name** | `image-to-3d-api` (or anything you want) |
| **Region** | Oregon (or closest to you) |
| **Branch** | `claude/2d-to-3d-environment-l0rm5` |
| **Root Directory** | `backend` |
| **Runtime** | Detected automatically (Python 3) |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn -c gunicorn_config.py app:app` |
| **Instance Type** | **Free** |

### 1.4 Deploy!
1. Click **"Create Web Service"** (at the bottom)
2. Wait 5-10 minutes while it builds
3. Watch the logs - you'll see packages installing
4. When you see "✅ Build successful", it's ready!

### 1.5 Copy Your API URL
At the top of the page, you'll see your URL:
```
https://image-to-3d-api-xxxx.onrender.com
```

**📋 COPY THIS URL - YOU'LL NEED IT IN STEP 2!**

### 1.6 Test It Works
1. Click on your URL or paste it in a new tab
2. You should see JSON that starts with:
```json
{
  "status": "online",
  "service": "Image to 3D Environment Generator",
  ...
}
```

✅ **Backend is live!**

---

## Step 2: Update Frontend API URL (3 minutes)

Now we need to tell the frontend where the backend is.

### 2.1 Go to GitHub
1. Go to: **https://github.com/RattusKing/Allspace**
2. Make sure you're on branch: `claude/2d-to-3d-environment-l0rm5`
   - (dropdown near top left should show this branch)

### 2.2 Edit the JavaScript File
1. Click on the **"frontend"** folder
2. Click on **"app.js"**
3. Click the **pencil icon** (✏️) to edit (top right of file viewer)

### 2.3 Find and Update the API URL
1. Look for line 7 (or search for `API_URL`)
2. You'll see:
```javascript
const API_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:5000'
    : 'https://your-backend-url.onrender.com';
```

3. Replace `https://your-backend-url.onrender.com` with YOUR actual Render URL
4. Example:
```javascript
const API_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:5000'
    : 'https://image-to-3d-api-abcd.onrender.com';  // ← Your URL here
```

### 2.4 Commit the Change
1. Scroll to bottom of page
2. In "Commit message" box, type: `Update API URL for production`
3. Make sure "Commit directly to the claude/2d-to-3d-environment-l0rm5 branch" is selected
4. Click **"Commit changes"**

✅ **Frontend configured!**

---

## Step 3: Enable GitHub Pages (2 minutes)

### 3.1 Go to Repository Settings
1. In your repo, click **"Settings"** tab (top right area)
2. In the left sidebar, click **"Pages"**

### 3.2 Configure GitHub Pages
1. Under "Build and deployment":
   - **Source**: Select **"Deploy from a branch"**
   - **Branch**: Select **"claude/2d-to-3d-environment-l0rm5"** from dropdown
   - **Folder**: Select **"/ (root)"** from dropdown
2. Click **"Save"**

### 3.3 Wait for Deployment
1. You'll see a message: "Your site is live at..."
2. Wait 1-2 minutes for GitHub to build your site
3. Refresh the page to see status

### 3.4 Get Your Live URL
Your site will be at:
```
https://rattusking.github.io/Allspace/frontend/
```

or possibly:
```
https://rattusking.github.io/Allspace/frontend/index.html
```

✅ **Frontend is live!**

---

## Step 4: Test Your Live Application! 🎉

### 4.1 Visit Your Site
1. Open a new tab
2. Go to: `https://rattusking.github.io/Allspace/frontend/`

### 4.2 Try It Out!
1. You should see the beautiful dark interface
2. Drag and drop an image (or click browse)
3. Click **"Generate 3D Environment"**
4. Wait 30-90 seconds (first time may take longer)
5. See your 3D model!
6. Download as GLB or FBX

### 4.3 Share Your Link!
Your working application is now live at:
```
https://rattusking.github.io/Allspace/frontend/
```

Share it with friends, on social media, in your portfolio!

---

## 🎯 What You Just Created

✅ A fully working web application
✅ AI-powered image to 3D conversion
✅ Hosted completely free
✅ No terminal/command line used at all
✅ Professional and open-source

---

## 📱 Troubleshooting (All through web browser!)

### Problem: "Failed to fetch" error when generating

**Cause**: Backend is sleeping (Render free tier sleeps after 15 min)

**Fix**:
1. Open a new tab
2. Visit your Render URL directly: `https://image-to-3d-api-xxxx.onrender.com`
3. Wait 30 seconds for it to wake up
4. Go back to your site and try again

### Problem: GitHub Pages shows 404

**Cause**: Not deployed yet or wrong path

**Fix**:
1. Go to Settings → Pages on GitHub
2. Check that branch and folder are correct
3. Wait 2-3 minutes and refresh
4. Try different URLs:
   - `https://rattusking.github.io/Allspace/`
   - `https://rattusking.github.io/Allspace/frontend/`
   - `https://rattusking.github.io/Allspace/frontend/index.html`

### Problem: First generation takes forever

**Cause**: AI model downloading (one-time, ~100MB)

**Fix**: Just wait! After the first generation, it'll be fast (30-90 sec)

### View Render Logs (if needed)
1. Go to Render dashboard
2. Click on your service
3. Click "Logs" tab
4. See what's happening

---

## 🎊 You're Done!

You now have a live, working application that:
- Anyone can visit and use
- Converts images to 3D models
- Costs you $0
- Required zero terminal/command line

**Your live app**: https://rattusking.github.io/Allspace/frontend/

Enjoy your free, open-source Image to 3D Generator! 🚀

---

## Optional: Make Updates Later

Want to change something? All through the web:

1. Go to GitHub.com
2. Navigate to the file you want to change
3. Click the pencil icon (✏️)
4. Make your changes
5. Commit
6. Both Render and GitHub Pages auto-update!

No terminal needed, ever! 🎉
