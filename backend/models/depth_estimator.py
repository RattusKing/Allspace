"""
Depth Estimation Module
Uses Hugging Face Inference API for MiDaS depth estimation
"""

import os
import cv2
import numpy as np
import requests
from PIL import Image
import io


class DepthEstimator:
    """Estimates depth from 2D images using Hugging Face Inference API"""

    def __init__(self):
        """Initialize depth estimator with HF API"""
        self.api_token = os.getenv('HF_API_TOKEN')
        
        # Hugging Face model endpoint
        self.api_url = "https://api-inference.huggingface.co/models/Intel/dpt-large"
        
        if not self.api_token:
            print("⚠️  WARNING: HF_API_TOKEN not found in environment")
            print("   Set it in Render dashboard: Environment → Add HF_API_TOKEN")
            print("   Get token from: https://huggingface.co/settings/tokens")
        else:
            print("🔧 Depth Estimator ready (using Hugging Face API)")
            print("   ✅ API token configured")

    def estimate_depth(self, image_path):
        """
        Estimate depth map from image using HF Inference API

        Args:
            image_path: Path to input image

        Returns:
            depth_map: Normalized depth map (numpy array)
            confidence_map: Confidence/uncertainty map
        """
        try:
            # Check API token
            if not self.api_token:
                raise ValueError("HF_API_TOKEN environment variable not set")

            # Load and prepare image
            print(f"📤 Sending image to Hugging Face API...")
            with open(image_path, 'rb') as f:
                image_bytes = f.read()

            # Load original image for dimensions
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            original_height, original_width = img.shape[:2]
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Call Hugging Face Inference API
            headers = {"Authorization": f"Bearer {self.api_token}"}
            
            response = requests.post(
                self.api_url,
                headers=headers,
                data=image_bytes,
                timeout=60  # 60 second timeout
            )

            if response.status_code == 503:
                # Model is loading, wait and retry
                print("   Model loading on HF servers, waiting 20 seconds...")
                import time
                time.sleep(20)
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    data=image_bytes,
                    timeout=60
                )

            if response.status_code != 200:
                error_msg = f"HF API error {response.status_code}: {response.text}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)

            print("✅ Received depth map from HF API")

            # Parse response - HF returns a PIL Image
            depth_image = Image.open(io.BytesIO(response.content))
            
            # Convert to numpy array
            depth_map = np.array(depth_image)
            
            # If it's RGB, convert to grayscale
            if len(depth_map.shape) == 3:
                depth_map = cv2.cvtColor(depth_map, cv2.COLOR_RGB2GRAY)
            
            # Resize to match original image dimensions
            if depth_map.shape != (original_height, original_width):
                depth_map = cv2.resize(depth_map, (original_width, original_height))

            # Normalize depth map to 0-1 range
            depth_map = depth_map.astype(np.float32)
            if depth_map.max() > depth_map.min():
                depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())
            else:
                depth_map = depth_map / 255.0  # If already normalized

            # Invert so closer = higher values (standard convention)
            depth_map = 1.0 - depth_map

            # Calculate confidence map
            confidence_map = self._calculate_confidence(depth_map)

            print(f"✅ Depth map processed: {depth_map.shape}")

            return depth_map, confidence_map

        except requests.exceptions.Timeout:
            print("❌ HF API request timed out")
            raise Exception("Hugging Face API timeout - please try again")
        except requests.exceptions.RequestException as e:
            print(f"❌ HF API request failed: {e}")
            raise Exception(f"Failed to connect to Hugging Face API: {e}")
        except Exception as e:
            print(f"❌ Error estimating depth: {e}")
            raise

    def _calculate_confidence(self, depth_map):
        """
        Calculate confidence map based on depth gradients

        Args:
            depth_map: Input depth map

        Returns:
            confidence_map: Values 0-1, higher = more confident
        """
        # Calculate gradients
        grad_x = cv2.Sobel(depth_map, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(depth_map, cv2.CV_64F, 0, 1, ksize=3)

        # Calculate gradient magnitude
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Normalize
        if gradient_magnitude.max() > 0:
            gradient_magnitude = gradient_magnitude / gradient_magnitude.max()

        # Invert: low gradient = high confidence
        confidence_map = 1.0 - gradient_magnitude

        # Apply smoothing
        confidence_map = cv2.GaussianBlur(confidence_map, (5, 5), 0)

        return confidence_map

    def visualize_depth(self, depth_map, output_path=None):
        """
        Create a visualization of the depth map

        Args:
            depth_map: Input depth map
            output_path: Optional path to save visualization

        Returns:
            colored_depth: RGB visualization of depth
        """
        # Apply colormap
        depth_uint8 = (depth_map * 255).astype(np.uint8)
        colored_depth = cv2.applyColorMap(depth_uint8, cv2.COLORMAP_INFERNO)

        if output_path:
            cv2.imwrite(output_path, colored_depth)

        return colored_depth
