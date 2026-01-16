"""
Depth Estimation Module
Lightweight computer vision-based depth estimation
Optimized for low memory usage (<100MB RAM)
"""

import os
import cv2
import numpy as np


class DepthEstimator:
    """
    Estimates depth from 2D images using lightweight computer vision techniques.
    Memory-optimized for deployment on 512MB instances.
    """

    def __init__(self):
        """Initialize lightweight depth estimator"""
        print("🔧 Custom Depth Estimator initialized")
        print("   ✅ 100% free, no API required")
        print("   ✅ Fast local processing")
        print("   ✅ Memory-optimized (<100MB)")

    def estimate_depth(self, image_path):
        """
        Estimate depth map from image using lightweight CV algorithms
        Optimized for low memory usage (<100MB)

        Args:
            image_path: Path to input image

        Returns:
            depth_map: Normalized depth map (numpy array, 0=far, 1=close)
            confidence_map: Confidence/uncertainty map
        """
        try:
            print(f"🎨 Analyzing image for depth estimation...")

            # Load image with max size limit to save memory
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not load image: {image_path}")

            # Resize if too large (save memory)
            max_dim = 512
            height, width = img.shape[:2]
            if max(height, width) > max_dim:
                scale = max_dim / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = cv2.resize(img, (new_width, new_height))
                height, width = new_height, new_width
                print(f"   📏 Resized to {width}x{height} to save memory")

            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Simple depth estimation - memory efficient
            print("   📐 Computing depth map...")

            # 1. Perspective depth (Y-axis gradient) - 50%
            y_coords = np.linspace(1, 0, height, dtype=np.float32)
            perspective = np.tile(y_coords[:, np.newaxis], (1, width))

            # 2. Edge-based depth - 30%
            edges = cv2.Canny(img_gray, 50, 150)
            dist = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 5)
            edge_depth = 1.0 - self._normalize(dist)

            # 3. Simple brightness - 20%
            brightness = self._normalize(img_gray.astype(np.float32))

            # Weighted fusion (in-place to save memory)
            depth_map = (perspective * 0.5 + edge_depth * 0.3 + brightness * 0.2).astype(np.float32)

            # Clean up to free memory
            del perspective, edge_depth, brightness, edges, dist

            # Validate and normalize
            depth_map = np.nan_to_num(depth_map, nan=0.5, posinf=1.0, neginf=0.0)
            depth_map = self._normalize(depth_map)

            # Simple smoothing
            depth_map = cv2.GaussianBlur(depth_map, (5, 5), 0)
            depth_map = self._normalize(depth_map)

            # Simple confidence map (based on gradient)
            grad_x = cv2.Sobel(depth_map, cv2.CV_32F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(depth_map, cv2.CV_32F, 0, 1, ksize=3)
            gradient = np.sqrt(grad_x**2 + grad_y**2)
            confidence_map = 1.0 - self._normalize(gradient)
            confidence_map = cv2.GaussianBlur(confidence_map, (5, 5), 0)

            # Clean up
            del grad_x, grad_y, gradient, img_gray, img

            print(f"✅ Depth map generated: {depth_map.shape}")
            print(f"   Range: {depth_map.min():.3f} - {depth_map.max():.3f}")
            print(f"   Memory-optimized algorithm used")

            return depth_map, confidence_map

        except Exception as e:
            print(f"❌ Error estimating depth: {e}")
            raise

    def _normalize(self, array):
        """Normalize array to 0-1 range"""
        array = array.astype(np.float32)
        min_val = array.min()
        max_val = array.max()
        if max_val > min_val:
            return (array - min_val) / (max_val - min_val)
        return array / 255.0 if max_val > 1 else array

    def visualize_depth(self, depth_map, output_path=None):
        """
        Create a visualization of the depth map

        Args:
            depth_map: Input depth map
            output_path: Optional path to save visualization

        Returns:
            colored_depth: RGB visualization of depth
        """
        # Apply colormap (INFERNO: dark purple=far, bright yellow=close)
        depth_uint8 = (depth_map * 255).astype(np.uint8)
        colored_depth = cv2.applyColorMap(depth_uint8, cv2.COLORMAP_INFERNO)

        if output_path:
            cv2.imwrite(output_path, colored_depth)
            print(f"💾 Depth visualization saved: {output_path}")

        return colored_depth
