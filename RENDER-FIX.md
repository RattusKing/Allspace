# 🔧 Render Deployment Notes

Allspace is a lightweight Flask app built on classical OpenCV computer vision. There is **no PyTorch, no MiDaS, no Open3D, and no ML model download** — nothing heavy to install and nothing to fetch at runtime. As a result the build is small and the service starts in seconds, well within Render's free tier.

> Earlier versions of this document described fixes for PyTorch/MiDaS/Open3D build and memory errors, lazy model loading, and a `torch.hub` `Authorization` bug. None of that applies anymore — the project no longer uses any of those libraries.

---

## Current Render settings

Create a new Web Service on [render.com](https://render.com), connect the `Allspace` repository, and configure:

| Setting | Value |
|---------|-------|
| **Root Directory** | `backend` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn --bind 0.0.0.0:$PORT app:app` |
| **Instance Type** | Free |

> The repository also includes `gunicorn_config.py`, so `gunicorn -c gunicorn_config.py app:app` works as an alternative start command (it binds to `$PORT` automatically). The `render.yaml` blueprint in the repo uses that form.

Because Flask serves `index.html` at `/`, deploying the backend deploys the whole app. Open the Render service URL directly in a browser to use it.

---

## Notes

- **Cold starts**: On the free tier the service sleeps after ~15 minutes of inactivity; the first request afterward takes a few seconds to wake it.
- **No model download**: Generation is pure CPU OpenCV work, so there is no one-time model download and no first-run delay for downloading weights.
- **Memory**: The app's footprint is small; the free tier's RAM is sufficient for normal floor-plan images. Very large images are downscaled internally before processing.
