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
        Estimate depth map from image using scene-aware CV algorithms
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
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Detect scene type to apply appropriate depth strategy
            print("   🔍 Detecting scene type...")
            scene_type = self._detect_scene_type(img_gray, img_rgb, height, width)
            print(f"   📌 Scene type: {scene_type}")

            # Scene-specific depth estimation
            print("   📐 Computing scene-aware depth map...")

            if scene_type == "indoor_room":
                depth_map = self._indoor_depth(img_gray, height, width)
            elif scene_type == "outdoor_landscape":
                depth_map = self._landscape_depth(img_gray, height, width)
            elif scene_type == "portrait":
                depth_map = self._portrait_depth(img_gray, img_rgb, height, width)
            else:  # general/unknown
                depth_map = self._general_depth(img_gray, height, width)

            # Apply edge-aware refinement
            edges = cv2.Canny(img_gray, 50, 150)
            dist = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 5)
            edge_influence = 1.0 - self._normalize(dist)

            # Blend depth with edge information
            depth_map = depth_map * 0.7 + edge_influence * 0.3

            # Clean up
            del edges, dist, edge_influence

            # Validate and normalize
            depth_map = np.nan_to_num(depth_map, nan=0.5, posinf=1.0, neginf=0.0)
            depth_map = self._normalize(depth_map)

            # Smooth while preserving edges
            depth_map = cv2.bilateralFilter(depth_map, 9, 75, 75)
            depth_map = self._normalize(depth_map)

            # Simple confidence map (based on gradient)
            grad_x = cv2.Sobel(depth_map, cv2.CV_32F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(depth_map, cv2.CV_32F, 0, 1, ksize=3)
            gradient = np.sqrt(grad_x**2 + grad_y**2)
            confidence_map = 1.0 - self._normalize(gradient)
            confidence_map = cv2.GaussianBlur(confidence_map, (5, 5), 0)

            # Clean up
            del grad_x, grad_y, gradient, img_gray, img_rgb, img

            print(f"✅ Depth map generated: {depth_map.shape}")
            print(f"   Range: {depth_map.min():.3f} - {depth_map.max():.3f}")
            print(f"   Scene-aware algorithm used ({scene_type})")

            return depth_map, confidence_map

        except Exception as e:
            print(f"❌ Error estimating depth: {e}")
            raise

    def _detect_scene_type(self, img_gray, img_rgb, height, width):
        """Detect scene type to apply appropriate depth strategy"""

        # Check for horizontal lines (indoor rooms often have strong horizontal edges)
        edges = cv2.Canny(img_gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=width//4, maxLineGap=20)

        horizontal_lines = 0
        vertical_lines = 0

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = abs(np.arctan2(y2 - y1, x2 - x1))
                if angle < 0.3 or angle > (np.pi - 0.3):  # Horizontal
                    horizontal_lines += 1
                elif abs(angle - np.pi/2) < 0.3:  # Vertical
                    vertical_lines += 1

        # Check color saturation (landscapes tend to be more saturated)
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        saturation = hsv[:,:,1]
        avg_saturation = np.mean(saturation)

        # Check if image is centered (portraits often have centered subjects)
        center_brightness = np.mean(img_gray[height//4:3*height//4, width//4:3*width//4])
        edge_brightness = (np.mean(img_gray[:height//4, :]) + np.mean(img_gray[3*height//4:, :]) +
                          np.mean(img_gray[:, :width//4]) + np.mean(img_gray[:, 3*width//4:])) / 4
        center_contrast = center_brightness - edge_brightness

        del edges, hsv, saturation

        # Classify scene
        if horizontal_lines > 5 and vertical_lines > 3:
            return "indoor_room"
        elif avg_saturation > 100 and horizontal_lines < 3:
            return "outdoor_landscape"
        elif center_contrast > 30:
            return "portrait"
        else:
            return "general"

    def _indoor_depth(self, img_gray, height, width):
        """Depth estimation for indoor rooms"""
        # Strong perspective from floor/ceiling
        y_coords = np.linspace(1, 0, height, dtype=np.float32)
        depth = np.tile(y_coords[:, np.newaxis], (1, width))

        # Darken = further for indoor scenes
        brightness = self._normalize(img_gray.astype(np.float32))
        depth = depth * 0.6 + (1.0 - brightness) * 0.4

        return depth

    def _landscape_depth(self, img_gray, height, width):
        """Depth estimation for outdoor landscapes"""
        # Sky is far, ground is closer
        y_coords = np.linspace(0.9, 0.1, height, dtype=np.float32)
        depth = np.tile(y_coords[:, np.newaxis], (1, width))

        # Contrast = closer for outdoor
        mean = cv2.blur(img_gray.astype(np.float32), (15, 15))
        mean_sq = cv2.blur(img_gray.astype(np.float32)**2, (15, 15))
        variance = mean_sq - mean**2
        contrast = self._normalize(variance)

        depth = depth * 0.5 + contrast * 0.5
        del mean, mean_sq, variance

        return depth

    def _portrait_depth(self, img_gray, img_rgb, height, width):
        """Depth estimation for portraits/people"""
        # Center is closer, edges are background
        y, x = np.ogrid[:height, :width]
        center_y, center_x = height / 2, width / 2

        # Distance from center
        dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        max_dist = np.sqrt(center_x**2 + center_y**2)
        depth = 1.0 - self._normalize(dist_from_center)

        # Bright = closer for portraits
        brightness = self._normalize(img_gray.astype(np.float32))
        depth = depth * 0.6 + brightness * 0.4

        del dist_from_center
        return depth

    def _general_depth(self, img_gray, height, width):
        """General depth estimation for unknown scenes"""
        # Balanced approach
        y_coords = np.linspace(0.8, 0.2, height, dtype=np.float32)
        perspective = np.tile(y_coords[:, np.newaxis], (1, width))

        brightness = self._normalize(img_gray.astype(np.float32))

        return perspective * 0.6 + brightness * 0.4

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
