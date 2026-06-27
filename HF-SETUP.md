# 🤗 Hugging Face Setup — Obsolete

**This document is obsolete. No setup is required.**

Allspace does **not** use any hosted machine-learning model. There is no Hugging Face Inference API, no `HF_API_TOKEN`, and no DPT-Large / MiDaS depth model anywhere in the project.

The 2D → 3D pipeline runs entirely on the CPU using classical OpenCV computer vision (scene classification, a binary wall mask, and wall extrusion into 3D geometry). Nothing is sent to an external inference service, and there are no API tokens or environment variables to configure.

If you previously set an `HF_API_TOKEN` environment variable on Render or elsewhere, you can safely remove it.

For how the real pipeline works, see `README.md`, and for a detailed technical breakdown see `FLOORPLAN-DIAGNOSIS.md`.
