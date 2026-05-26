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

            # Compute edge map once (shared across scene types)
            edges = cv2.Canny(img_gray, 50, 150)
            dist = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 5)
            edge_depth = self._normalize(dist)

            # Apply scene-specific depth estimation
            if scene_type == "floor_plan":
                depth_map = self._floorplan_depth(img_gray, height, width)
                depth_map = self._normalize(depth_map)
                confidence_map = np.ones_like(depth_map) * 0.95
                del edges, dist, edge_depth, img_gray, img_rgb, img
                print(f"✅ Depth map created: {depth_map.shape}")
                print(f"   Range: {depth_map.min():.3f} - {depth_map.max():.3f}")
                return depth_map, confidence_map, scene_type

            elif scene_type == "building_facade":
                # Facade depth uses layer-based assignment (sky/wall/ground/windows)
                # rather than a noisy gradient – this drives the proper box mesh.
                depth_map = self._facade_depth(img_gray, img_rgb, height, width)
                confidence_map = np.ones_like(depth_map) * 0.90
                del edges, dist, edge_depth, img_gray, img_rgb, img
                print(f"✅ Facade depth map: {depth_map.shape}, "
                      f"range {depth_map.min():.3f} – {depth_map.max():.3f}")
                return depth_map, confidence_map, scene_type

            elif scene_type == "indoor_room":
                depth_map = self._indoor_depth(img_gray, img_rgb, height, width)
            elif scene_type == "outdoor_landscape":
                depth_map = self._landscape_depth(img_gray, img_rgb, height, width)
            elif scene_type == "portrait":
                depth_map = self._portrait_depth(img_gray, img_rgb, height, width)
            else:
                depth_map = self._general_depth(img_gray, img_rgb, height, width)

            # Blend with edge-distance refinement (edges = depth discontinuities)
            depth_map = depth_map * 0.75 + edge_depth * 0.25
            depth_map = self._normalize(depth_map)

            # Edge-preserving bilateral filter instead of Gaussian blur
            depth_float = depth_map.astype(np.float32)
            depth_map = cv2.bilateralFilter(depth_float, d=9, sigmaColor=0.15, sigmaSpace=15)
            depth_map = self._normalize(depth_map)

            # Wider depth range (0.05-0.95 = 90% variation for strong 3D effect)
            depth_map = 0.05 + depth_map * 0.90

            # Build confidence from edge strength
            confidence_map = 1.0 - (self._normalize(edges.astype(np.float32)) * 0.3)
            confidence_map = cv2.bilateralFilter(
                confidence_map.astype(np.float32), d=9, sigmaColor=0.15, sigmaSpace=15
            )

            del edges, dist, edge_depth, img_gray, img_rgb, img

            print(f"✅ Depth map created: {depth_map.shape}")
            print(f"   Range: {depth_map.min():.3f} - {depth_map.max():.3f}")
            print(f"   Style: Multi-cue, edge-preserving depth estimation")

            return depth_map, confidence_map, scene_type

        except Exception as e:
            print(f"❌ Error estimating depth: {e}")
            raise

    def _detect_scene_type(self, img_gray, img_rgb, height, width):
        """Detect scene type to apply appropriate depth strategy"""

        # ── Sky / open-boundary analysis ────────────────────────────────────
        # A building FACADE has sky (bright, open, touching the top border).
        # A FLOOR PLAN has enclosed white rooms – no sky strip at the top.
        top_strip    = img_gray[:height // 5, :]
        bottom_strip = img_gray[4 * height // 5:, :]
        mid_strip    = img_gray[height // 5: 4 * height // 5, :]

        top_brightness    = float(np.mean(top_strip))
        mid_brightness    = float(np.mean(mid_strip))
        bottom_brightness = float(np.mean(bottom_strip))

        # "Sky at top": top border is noticeably brighter than the middle AND
        # a large fraction of the top strip is near-white (open sky / paper sky).
        top_bright_fraction = float(np.sum(top_strip > 200)) / top_strip.size
        bottom_bright_fraction = float(np.sum(bottom_strip > 200)) / bottom_strip.size

        # Key distinction: real sky is only bright at the TOP (not bottom).
        # Floor plan white paper is bright THROUGHOUT (top AND bottom ≈ equal).
        # If bottom is also very white, it's a paper background — not sky.
        white_throughout = (top_bright_fraction > 0.40 and bottom_bright_fraction > 0.35)

        sky_at_top = (top_brightness > 180
                      and top_bright_fraction > 0.35
                      and top_brightness > mid_brightness + 15
                      and not white_throughout)

        # ── Structural line analysis (shared by floor-plan and facade) ───────
        edges = cv2.Canny(img_gray, 50, 150)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, 30,
            minLineLength=width // 6, maxLineGap=30
        )
        horizontal_lines = 0
        vertical_lines   = 0
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = abs(np.arctan2(y2 - y1, x2 - x1))
                if angle < 0.3 or angle > (np.pi - 0.3):
                    horizontal_lines += 1
                elif abs(angle - np.pi / 2) < 0.3:
                    vertical_lines += 1

        has_many_straight_lines = (horizontal_lines + vertical_lines) > 8

        # ── Building facade detection (checked BEFORE floor plan) ─────────
        # Criteria: sky at top + building has significant structural lines.
        # Elevation drawings with coloured walls are also caught here.
        hsv_full = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        mid_saturation = float(np.mean(hsv_full[height // 5: 4 * height // 5, :, 1]))
        # Low saturation across the full image strongly suggests a monochrome drawing
        # (floor plan, section, elevation on paper) rather than a real photo facade.
        full_saturation = float(np.mean(hsv_full[:, :, 1]))
        del hsv_full

        # A facade also shows sky-to-ground brightness contrast
        sky_ground_contrast = abs(top_brightness - bottom_brightness)

        # A floor plan on white paper has very low colour saturation
        # (black lines on white background). Real building photos have more colour.
        is_low_saturation_drawing = full_saturation < 20

        is_building_facade = (
            sky_at_top
            and has_many_straight_lines
            and (mid_saturation > 15 or sky_ground_contrast > 25)
            and not is_low_saturation_drawing  # exclude monochrome architectural drawings
        )

        if is_building_facade:
            del edges
            print(f"  🏠 Building facade detected! "
                  f"sky_at_top={sky_at_top}, lines={horizontal_lines+vertical_lines}, "
                  f"mid_sat={mid_saturation:.1f}, sky_ground_contrast={sky_ground_contrast:.1f}")
            return "building_facade"

        # ── Floor plan detection ───────────────────────────────────────────
        avg_brightness = float(np.mean(img_gray))
        std_brightness = float(np.std(img_gray))
        dark_pixels  = np.sum(img_gray < 100)
        light_pixels = np.sum(img_gray > 200)
        total_pixels = img_gray.size

        dark_ratio  = dark_pixels  / total_pixels
        light_ratio = light_pixels / total_pixels

        is_mostly_white           = avg_brightness > 170
        is_high_contrast          = std_brightness > 35
        has_significant_dark_lines  = 0.02 < dark_ratio < 0.5
        has_significant_white_space = light_ratio > 0.35

        conditions_met = sum([
            is_mostly_white and has_significant_white_space,
            is_high_contrast,
            has_significant_dark_lines,
            has_many_straight_lines,
        ])
        strong_floor_plan = is_mostly_white and has_significant_white_space and is_high_contrast

        # A monochrome drawing (low saturation) with uniform white background is
        # almost certainly a floor plan, even if it accidentally triggers sky_at_top.
        is_architectural_drawing = is_low_saturation_drawing and white_throughout and has_many_straight_lines

        # Classify as floor_plan when:
        #  (a) sky-at-top NOT triggered (no sky = not a facade photo), OR
        #  (b) image is a low-saturation architectural drawing (safe override)
        if (not sky_at_top or is_architectural_drawing) and (conditions_met >= 2 or strong_floor_plan):
            del edges
            print(f"  📐 Floor plan detected! conditions={conditions_met}/4 "
                  f"(white={is_mostly_white}, contrast={is_high_contrast}, "
                  f"dark_lines={has_significant_dark_lines}, straight={has_many_straight_lines}, "
                  f"drawing={is_architectural_drawing})")
            return "floor_plan"

        # ── Other scene types ──────────────────────────────────────────────
        hsv2 = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        avg_saturation = float(np.mean(hsv2[:, :, 1]))
        del hsv2

        center_brightness = float(np.mean(
            img_gray[height // 4: 3 * height // 4, width // 4: 3 * width // 4]
        ))
        edge_brightness = float(
            (np.mean(img_gray[:height // 4, :])
             + np.mean(img_gray[3 * height // 4:, :])
             + np.mean(img_gray[:, :width // 4])
             + np.mean(img_gray[:, 3 * width // 4:])) / 4
        )
        center_contrast = center_brightness - edge_brightness

        del edges

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
        Phase 1: Clean binary wall mask for architectural floor plan drawings.

        Grayscale value ranges for typical CAD floor plans:
          Dark navy/black walls  →   0 – 80   (kept)
          Cyan/blue annotations  → 140 – 200  (excluded by threshold)
          White paper            → 220 – 255  (excluded by threshold)

        Pipeline:
          1. Threshold at 100  → captures walls + text, excludes cyan/light ink
          2. Two-stage close   → first fills line-width gaps, then fills the
                                 white body between parallel wall face lines
          3. Open (erode+dilate) pass to destroy tiny isolated blobs (text) that
             didn't grow large enough during closing
          4. Connected-component area filter as final guard
        """
        min_dim = min(height, width)

        # ── Step 1: Find dark structural pixels ──────────────────────────────
        # 120 catches dark navy/black walls (grayscale 0-80) and JPEG-bloomed
        # edge pixels (80-120) without picking up cyan annotations (~150+).
        _, dark = cv2.threshold(img_gray, 120, 255, cv2.THRESH_BINARY_INV)
        # Remove single-pixel speckles
        dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))

        # ── Step 2: Two-stage morphological close ─────────────────────────────
        # Stage A – small close: fuses stroke pixel gaps caused by JPEG artifacts
        ck1 = max(3, min_dim // 80)              # ~4 px at 350 px
        stage_a = cv2.morphologyEx(
            dark, cv2.MORPH_CLOSE, np.ones((ck1, ck1), np.uint8)
        )
        del dark

        # Stage B – larger close: bridges the white body gap between the two
        # parallel face lines that CAD drawings use to represent wall thickness.
        # Walls at 1:100 on a 96 Dpi scan leave a 4-14 px gap at 640 px.
        ck2 = max(7, min_dim // 35)              # ~10 px at 350 px, ~18 px at 640 px
        stage_b = cv2.morphologyEx(
            stage_a, cv2.MORPH_CLOSE,
            np.ones((ck2, ck2), np.uint8), iterations=2
        )
        del stage_a

        # NOTE: No open/erode pass here.  The open pass in the previous version
        # destroyed single-line walls (2-4 px wide) because they don't grow
        # wide enough for the open kernel to spare them.  Text removal is
        # handled solely by the area filter below.

        # ── Step 3: Connected-component area filter ───────────────────────────
        # Single wall lines stay narrow after closing (close fills gaps, not
        # width).  Multiple nearby lines merge into larger blobs.  Text
        # characters form small isolated blobs that rarely exceed 0.3 % of the
        # image area; the 0.3 % floor discards them.
        n, labels, stats, _ = cv2.connectedComponentsWithStats(stage_b, connectivity=8)
        del stage_b

        wall_mask = np.zeros((height, width), dtype=np.uint8)
        min_area = max(200, int(width * height * 0.003))   # 0.3 % min
        max_area = int(width * height * 0.45)
        kept = 0
        for i in range(1, n):
            a = int(stats[i, cv2.CC_STAT_AREA])
            if min_area <= a <= max_area:
                wall_mask[labels == i] = 255
                kept += 1
        del labels, stats

        # Light dilation to give thin surviving wall lines a few extra pixels
        # of body so contour extrusion in the mesh generator sees solid quads.
        wall_mask = cv2.dilate(wall_mask, np.ones((3, 3), np.uint8), iterations=1)

        depth = np.zeros((height, width), dtype=np.float32)
        depth[wall_mask > 0] = 1.0
        del wall_mask

        wall_pct = float(np.mean(depth > 0)) * 100
        print(f"  🏗️  Floor plan: {n - 1} dark components → "
              f"{kept} wall blobs, {wall_pct:.1f}% wall coverage")

        return depth

    def _facade_depth(self, img_gray, img_rgb, height, width):
        """
        Depth for building facade / elevation images.

        Assigns physically plausible depth layers:
          Sky   → very far   (0.00 – 0.10)
          Wall  → mid        (0.42 – 0.50, flat front face)
          Windows → recessed (wall − 0.08)
          Roof  → protruding (wall + 0.06)
          Ground → near      (0.65 – 0.95, perspective gradient)
        """
        row_means = np.mean(img_gray.astype(np.float32), axis=1)

        # ── Find sky / building / ground boundaries ───────────────────────
        top_brightness = float(np.mean(row_means[:height // 5]))
        sky_threshold  = top_brightness * 0.80

        sky_end = height // 5  # default
        for r in range(height // 10, height // 2):
            if row_means[r] < sky_threshold:
                sky_end = r
                break

        # Ground starts where rows get darker again near the bottom
        ground_start = int(height * 0.88)
        for r in range(height - 1, height // 2, -1):
            if row_means[r] < float(np.mean(row_means[3 * height // 4:])) * 0.95:
                ground_start = r
                break

        building_top    = max(0, sky_end)
        building_bottom = min(height, ground_start)
        building_depth_val = 0.46   # depth of the flat facade wall

        depth = np.full((height, width), building_depth_val, dtype=np.float32)

        # Sky: gradient from 0 (very top) to 0.10 (just above building)
        if building_top > 0:
            sky_grad = np.linspace(0.0, 0.10, building_top, dtype=np.float32)
            depth[:building_top, :] = sky_grad[:, np.newaxis]

        # Ground: perspective gradient from 0.65 (horizon) to 0.95 (camera foot)
        if building_bottom < height:
            rows_ground = height - building_bottom
            ground_grad = np.linspace(0.65, 0.95, rows_ground, dtype=np.float32)
            depth[building_bottom:, :] = ground_grad[:, np.newaxis]

        # ── Window detection: bright or dark rectangular patches in the wall ─
        if building_top < building_bottom:
            wall_slice = img_gray[building_top:building_bottom, :]
            wall_med   = float(np.median(wall_slice))

            # Windows brighter than the wall (common in drawings / renders)
            bright_win = (wall_slice.astype(np.float32) > wall_med + 18).astype(np.float32)
            # Windows darker than the wall (deep-set openings in photos)
            dark_win   = (wall_slice.astype(np.float32) < wall_med - 18).astype(np.float32)

            recess_amount   = 0.08
            protrude_amount = 0.06   # roofline / overhang

            depth[building_top:building_bottom, :] -= bright_win * recess_amount
            depth[building_top:building_bottom, :] -= dark_win   * recess_amount

            # Roofline band: top 5 % of the building region protrudes slightly
            roof_band = max(1, (building_bottom - building_top) // 20)
            depth[building_top: building_top + roof_band, :] += protrude_amount

        # Smooth transitions at sky/wall and wall/ground junctions
        blend = 12
        for i in range(blend):
            t = (i + 1) / (blend + 1)
            r_top = building_top + i
            r_bot = building_bottom - blend + i
            if 0 < r_top < height:
                depth[r_top, :] = (
                    depth[max(0, r_top - 1), :] * (1 - t) + building_depth_val * t
                )
            if 0 <= r_bot < height:
                depth[r_bot, :] = (
                    building_depth_val * (1 - t) + depth[min(height - 1, r_bot + 1), :] * t
                )

        print(f"  🏠 Facade depth: sky_end={sky_end}, ground_start={ground_start}, "
              f"wall_depth={building_depth_val:.2f}")
        return self._normalize(depth)

    def _local_variance_map(self, img_gray, kernel=15):
        """
        Compute local variance map as a depth cue.
        Regions with high texture variance are typically closer to the camera.
        """
        img_f = img_gray.astype(np.float32)
        mean = cv2.blur(img_f, (kernel, kernel))
        mean_sq = cv2.blur(img_f ** 2, (kernel, kernel))
        variance = np.maximum(mean_sq - mean ** 2, 0)
        del mean, mean_sq
        return self._normalize(variance)

    def _indoor_depth(self, img_gray, img_rgb, height, width):
        """
        Depth estimation for indoor rooms.
        Uses perspective gradient, local texture variance, and brightness.
        """
        # 1. Vertical perspective: bottom of frame = closer (floor)
        y_coords = np.linspace(1.0, 0.1, height, dtype=np.float32)
        perspective = np.tile(y_coords[:, np.newaxis], (1, width))

        # 2. Local texture variance: textured surfaces (e.g. furniture) appear closer
        texture = self._local_variance_map(img_gray, kernel=15)

        # 3. Inverse brightness: darker areas in indoor scenes tend to be further away
        brightness = self._normalize(img_gray.astype(np.float32))
        inv_brightness = 1.0 - brightness

        # 4. Saturation drop: distant areas often appear slightly desaturated
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        saturation = self._normalize(hsv[:, :, 1].astype(np.float32))
        del hsv

        depth = (perspective * 0.45 + texture * 0.30
                 + inv_brightness * 0.15 + saturation * 0.10)
        return depth

    def _landscape_depth(self, img_gray, img_rgb, height, width):
        """
        Depth estimation for outdoor landscapes.
        Uses sky/ground gradient, texture variance, and atmospheric haze (blue channel).
        """
        # 1. Vertical gradient: sky=far (top), ground=near (bottom)
        y_coords = np.linspace(0.1, 1.0, height, dtype=np.float32)
        ground_gradient = np.tile(y_coords[:, np.newaxis], (1, width))

        # 2. Sky detection: bright + blue-dominant regions are sky (far)
        blue_channel = img_rgb[:, :, 2].astype(np.float32)
        red_channel = img_rgb[:, :, 0].astype(np.float32)
        sky_signal = self._normalize(np.maximum(blue_channel - red_channel, 0))
        sky_mask = 1.0 - sky_signal  # Sky = far = low depth

        # 3. Texture variance: textured ground = near
        texture = self._local_variance_map(img_gray, kernel=15)

        # 4. Atmospheric haze: distant objects appear hazier (lower contrast locally)
        #    Use inverse of local variance as a haze proxy
        haze = 1.0 - self._local_variance_map(img_gray, kernel=31)

        depth = (ground_gradient * 0.40 + sky_mask * 0.25
                 + texture * 0.20 + (1.0 - haze) * 0.15)
        del blue_channel, red_channel, sky_signal, haze
        return depth

    def _portrait_depth(self, img_gray, img_rgb, height, width):
        """
        Depth estimation for portraits.
        Foreground subject = near, background = far.
        Uses center bias, texture, and skin-tone detection.
        """
        y, x = np.ogrid[:height, :width]
        center_y, center_x = height / 2, width / 2

        # 1. Radial center bias (subject usually centered)
        dist_from_center = np.sqrt(
            ((x - center_x) / (width / 2)) ** 2 +
            ((y - center_y) / (height / 2)) ** 2
        )
        radial = 1.0 - np.clip(dist_from_center / 1.5, 0, 1)
        del dist_from_center

        # 2. Local texture: sharp in-focus subject = near, blurred background = far
        texture = self._local_variance_map(img_gray, kernel=11)

        # 3. Brightness: subjects tend to be well-lit (brighter)
        brightness = self._normalize(img_gray.astype(np.float32))

        # 4. Saturation: subjects usually more saturated than backgrounds
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        saturation = self._normalize(hsv[:, :, 1].astype(np.float32))
        del hsv

        depth = (radial * 0.40 + texture * 0.30
                 + brightness * 0.15 + saturation * 0.15)
        return depth

    def _general_depth(self, img_gray, img_rgb, height, width):
        """
        General depth estimation for unclassified scenes.
        Multi-cue: perspective gradient + texture + saturation.
        """
        # 1. Bottom-of-frame = near (universal perspective prior)
        y_coords = np.linspace(0.2, 1.0, height, dtype=np.float32)
        perspective = np.tile(y_coords[:, np.newaxis], (1, width))

        # 2. Texture variance: detail = near
        texture = self._local_variance_map(img_gray, kernel=15)

        # 3. Saturation: vivid colors tend to be closer
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        saturation = self._normalize(hsv[:, :, 1].astype(np.float32))
        del hsv

        # 4. Inverse brightness: slightly darker regions often further
        brightness = self._normalize(img_gray.astype(np.float32))

        depth = (perspective * 0.50 + texture * 0.25
                 + saturation * 0.15 + brightness * 0.10)
        return depth

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
