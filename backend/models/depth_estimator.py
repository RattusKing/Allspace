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
        Estimate depth map by analyzing image content
        Creates clean, scene-aware depth for professional 3D appearance

        Args:
            image_path: Path to input image

        Returns:
            depth_map: Normalized depth map (numpy array, 0=far, 1=close)
            confidence_map: Confidence/uncertainty map
        """
        try:
            print(f"🎨 Analyzing image for depth estimation...")

            # Load image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not load image: {image_path}")

            # Keep good quality for clean appearance
            max_dim = 640
            height, width = img.shape[:2]
            if max(height, width) > max_dim:
                scale = max_dim / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
                height, width = new_height, new_width
                print(f"   📏 Resized to {width}x{height}")

            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Detect scene type and use appropriate depth strategy
            scene_type = self._detect_scene_type(img_gray, img_rgb, height, width)
            print(f"   🔍 Detected scene type: {scene_type}")

            # Apply scene-specific depth estimation
            if scene_type == "floor_plan":
                # Floor plans get special treatment - walls are HIGH, floors are LOW
                depth_map = self._floorplan_depth(img_gray, height, width)
                # Light smoothing to keep walls crisp
                depth_map = cv2.GaussianBlur(depth_map, (5, 5), 0)
                depth_map = self._normalize(depth_map)
            elif scene_type == "indoor_room":
                depth_map = self._indoor_depth(img_gray, height, width)
                # Add edge-aware depth refinement
                edges = cv2.Canny(img_gray, 50, 150)
                dist = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 5)
                edge_depth = self._normalize(dist)
                # Blend with edge information (80% scene depth, 20% edge refinement)
                depth_map = depth_map * 0.8 + edge_depth * 0.2
                # Heavy smoothing for clean, professional appearance (NO jagged edges)
                depth_map = cv2.GaussianBlur(depth_map, (31, 31), 0)
                depth_map = self._normalize(depth_map)
            elif scene_type == "outdoor_landscape":
                depth_map = self._landscape_depth(img_gray, height, width)
                edges = cv2.Canny(img_gray, 50, 150)
                dist = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 5)
                edge_depth = self._normalize(dist)
                depth_map = depth_map * 0.8 + edge_depth * 0.2
                depth_map = cv2.GaussianBlur(depth_map, (31, 31), 0)
                depth_map = self._normalize(depth_map)
            elif scene_type == "portrait":
                depth_map = self._portrait_depth(img_gray, img_rgb, height, width)
                edges = cv2.Canny(img_gray, 50, 150)
                dist = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 5)
                edge_depth = self._normalize(dist)
                depth_map = depth_map * 0.8 + edge_depth * 0.2
                depth_map = cv2.GaussianBlur(depth_map, (31, 31), 0)
                depth_map = self._normalize(depth_map)
            else:
                depth_map = self._general_depth(img_gray, height, width)
                edges = cv2.Canny(img_gray, 50, 150)
                dist = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 5)
                edge_depth = self._normalize(dist)
                depth_map = depth_map * 0.8 + edge_depth * 0.2
                depth_map = cv2.GaussianBlur(depth_map, (31, 31), 0)
                depth_map = self._normalize(depth_map)

            # Use different depth ranges based on scene type
            if scene_type == "floor_plan":
                # Floor plans use FULL range (0.0-1.0) for actual room height
                # 0.0 = floor level, 1.0 = ceiling height (8-10 feet)
                depth_map = depth_map  # Already 0-1, keep full range
                confidence_map = np.ones_like(depth_map) * 0.95  # High confidence for floor plans
            else:
                # Other scenes use moderate depth range (0.2-0.8 = 60% variation)
                depth_map = 0.2 + depth_map * 0.6
                # Confidence based on edge strength
                confidence_map = 1.0 - (self._normalize(edges.astype(np.float32)) * 0.3)
                confidence_map = cv2.GaussianBlur(confidence_map, (11, 11), 0)

            # Clean up
            del edges, dist, edge_depth, img_gray, img_rgb, img

            print(f"✅ Depth map created: {depth_map.shape}")
            print(f"   Range: {depth_map.min():.3f} - {depth_map.max():.3f} (moderate 3D effect)")
            print(f"   Style: Clean, scene-aware depth estimation")

            return depth_map, confidence_map

        except Exception as e:
            print(f"❌ Error estimating depth: {e}")
            raise

    def _detect_scene_type(self, img_gray, img_rgb, height, width):
        """Detect scene type to apply appropriate depth strategy"""

        # Check for floor plan characteristics first (high priority)
        # Floor plans have: mostly white background, dark walls, many rectangular shapes

        # Calculate color distribution
        avg_brightness = np.mean(img_gray)
        std_brightness = np.std(img_gray)

        # Count pixels that are very dark (walls) vs very light (floors/rooms)
        dark_pixels = np.sum(img_gray < 100)  # Dark walls
        light_pixels = np.sum(img_gray > 200)  # White floors/background
        total_pixels = img_gray.size

        dark_ratio = dark_pixels / total_pixels
        light_ratio = light_pixels / total_pixels

        # Floor plans typically have:
        # - High average brightness (mostly white)
        # - High contrast (dark walls vs white floors)
        # - Many straight lines (both horizontal and vertical)
        is_mostly_white = avg_brightness > 200
        is_high_contrast = std_brightness > 60
        has_significant_dark_lines = dark_ratio > 0.05 and dark_ratio < 0.3
        has_significant_white_space = light_ratio > 0.5

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

        has_many_straight_lines = (horizontal_lines + vertical_lines) > 10

        # Detect floor plan (PRIMARY USE CASE)
        if (is_mostly_white and is_high_contrast and
            has_significant_dark_lines and has_significant_white_space and
            has_many_straight_lines):
            del edges
            return "floor_plan"

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

        # Classify other scene types
        if horizontal_lines > 5 and vertical_lines > 3:
            return "indoor_room"
        elif avg_saturation > 100 and horizontal_lines < 3:
            return "outdoor_landscape"
        elif center_contrast > 30:
            return "portrait"
        else:
            return "general"

    def _floorplan_depth(self, img_gray, height, width):
        """
        Depth estimation for architectural floor plans
        WALLS (dark pixels) = HIGH depth (extrude up to ceiling)
        FLOORS (white pixels) = LOW depth (ground level)
        """
        # Invert brightness: dark = high (walls), light = low (floors)
        # This is opposite of typical photo depth!
        inverted = 255 - img_gray
        depth = self._normalize(inverted.astype(np.float32))

        # Enhance wall detection with thresholding
        # Anything darker than 150 is likely a wall
        wall_mask = img_gray < 150
        floor_mask = img_gray > 200

        # Set walls to maximum height (1.0 = ceiling height)
        # Set floors to minimum height (0.0 = ground level)
        depth[wall_mask] = 1.0  # Walls at full ceiling height
        depth[floor_mask] = 0.0  # Floors at ground level

        # Areas in between (150-200) get gradient depth
        mid_mask = (img_gray >= 150) & (img_gray <= 200)
        if np.any(mid_mask):
            mid_values = 1.0 - self._normalize(img_gray[mid_mask].astype(np.float32))
            depth[mid_mask] = mid_values

        return depth

    def _indoor_depth(self, img_gray, height, width):
        """Depth estimation for indoor rooms - subtle for photo-like appearance"""
        # Gentle perspective from floor/ceiling
        y_coords = np.linspace(0.7, 0.3, height, dtype=np.float32)
        depth = np.tile(y_coords[:, np.newaxis], (1, width))

        # Very subtle brightness influence
        brightness = self._normalize(img_gray.astype(np.float32))
        depth = depth * 0.85 + (1.0 - brightness) * 0.15

        return depth

    def _landscape_depth(self, img_gray, height, width):
        """Depth estimation for outdoor landscapes - subtle for photo-like appearance"""
        # Gentle sky to ground gradient
        y_coords = np.linspace(0.7, 0.3, height, dtype=np.float32)
        depth = np.tile(y_coords[:, np.newaxis], (1, width))

        # Very subtle contrast influence
        mean = cv2.blur(img_gray.astype(np.float32), (15, 15))
        mean_sq = cv2.blur(img_gray.astype(np.float32)**2, (15, 15))
        variance = mean_sq - mean**2
        contrast = self._normalize(variance)

        depth = depth * 0.85 + contrast * 0.15
        del mean, mean_sq, variance

        return depth

    def _portrait_depth(self, img_gray, img_rgb, height, width):
        """Depth estimation for portraits/people - subtle for photo-like appearance"""
        # Very gentle center focus
        y, x = np.ogrid[:height, :width]
        center_y, center_x = height / 2, width / 2

        # Distance from center (much less dramatic)
        dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        max_dist = np.sqrt(center_x**2 + center_y**2)
        radial = 1.0 - self._normalize(dist_from_center)

        # Compress to small range (0.4 to 0.6)
        depth = 0.4 + radial * 0.2

        # Very subtle brightness
        brightness = self._normalize(img_gray.astype(np.float32))
        depth = depth * 0.9 + brightness * 0.1

        del dist_from_center
        return depth

    def _general_depth(self, img_gray, height, width):
        """General depth estimation for unknown scenes - subtle for photo-like appearance"""
        # Very gentle gradient
        y_coords = np.linspace(0.6, 0.4, height, dtype=np.float32)
        perspective = np.tile(y_coords[:, np.newaxis], (1, width))

        brightness = self._normalize(img_gray.astype(np.float32))

        # Mostly flat with subtle variation
        return perspective * 0.8 + brightness * 0.2

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
