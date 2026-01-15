"""
Depth Estimation Module
Custom computer vision-based depth estimation using multiple techniques
100% free, no API dependencies, fast processing
"""

import os
import cv2
import numpy as np
from scipy import ndimage


class DepthEstimator:
    """
    Estimates depth from 2D images using advanced computer vision techniques.
    Combines multiple methods for high-quality depth estimation:
    - Perspective-based depth (vanishing points, horizon detection)
    - Edge detection and segmentation
    - Texture and frequency analysis
    - Color/brightness atmospheric perspective
    - Saliency-based foreground detection
    """

    def __init__(self):
        """Initialize custom depth estimator"""
        print("🔧 Custom Depth Estimator initialized")
        print("   ✅ 100% free, no API required")
        print("   ✅ Fast local processing")
        print("   ✅ Multi-technique fusion algorithm")

    def estimate_depth(self, image_path):
        """
        Estimate depth map from image using custom CV algorithms

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

            height, width = img.shape[:2]
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Initialize depth maps from different techniques
            depth_maps = []
            weights = []

            # 1. PERSPECTIVE DEPTH (30% weight)
            print("   📐 Computing perspective depth...")
            perspective_depth = self._perspective_depth(img_gray, height, width)
            depth_maps.append(perspective_depth)
            weights.append(0.30)

            # 2. EDGE-BASED DEPTH (25% weight)
            print("   🔲 Analyzing edges and boundaries...")
            edge_depth = self._edge_based_depth(img_gray)
            depth_maps.append(edge_depth)
            weights.append(0.25)

            # 3. ATMOSPHERIC/COLOR DEPTH (20% weight)
            print("   🌫️  Applying atmospheric perspective...")
            atmospheric_depth = self._atmospheric_depth(img_rgb, img_gray)
            depth_maps.append(atmospheric_depth)
            weights.append(0.20)

            # 4. TEXTURE/FREQUENCY DEPTH (15% weight)
            print("   📊 Analyzing texture frequency...")
            texture_depth = self._texture_depth(img_gray)
            depth_maps.append(texture_depth)
            weights.append(0.15)

            # 5. SALIENCY-BASED DEPTH (10% weight)
            print("   👁️  Detecting salient foreground regions...")
            saliency_depth = self._saliency_depth(img)
            depth_maps.append(saliency_depth)
            weights.append(0.10)

            # FUSION: Weighted combination
            print("   🔄 Fusing depth estimates...")
            depth_map = np.zeros_like(depth_maps[0], dtype=np.float32)
            for depth, weight in zip(depth_maps, weights):
                # Ensure no NaN or Inf values
                depth = np.nan_to_num(depth, nan=0.0, posinf=1.0, neginf=0.0)
                depth_map += depth * weight

            # Normalize final depth map
            depth_map = self._normalize(depth_map)

            # Validate depth map has variation
            if np.isnan(depth_map).any() or np.isinf(depth_map).any():
                print("   ⚠️  NaN/Inf detected, cleaning...")
                depth_map = np.nan_to_num(depth_map, nan=0.5, posinf=1.0, neginf=0.0)

            depth_range = depth_map.max() - depth_map.min()
            if depth_range < 0.01:  # No variation
                print("   ⚠️  Depth map has no variation, using simple gradient...")
                # Fallback: simple vertical gradient
                y_coords = np.linspace(0, 1, height)
                depth_map = np.tile(y_coords[:, np.newaxis], (1, width))
                depth_map = self._normalize(depth_map)

            # Post-processing: bilateral filter to smooth while preserving edges
            try:
                depth_map = cv2.bilateralFilter(
                    depth_map.astype(np.float32),
                    d=9,
                    sigmaColor=75,
                    sigmaSpace=75
                )
                depth_map = self._normalize(depth_map)
            except Exception as e:
                print(f"   ⚠️  Bilateral filter failed: {e}, skipping...")

            # Calculate confidence map
            confidence_map = self._calculate_confidence(depth_map, depth_maps)

            print(f"✅ Depth map generated: {depth_map.shape}")
            print(f"   Range: {depth_map.min():.3f} - {depth_map.max():.3f}")
            print(f"   Mean: {depth_map.mean():.3f}, Std: {depth_map.std():.3f}")

            return depth_map, confidence_map

        except Exception as e:
            print(f"❌ Error estimating depth: {e}")
            raise

    def _perspective_depth(self, img_gray, height, width):
        """
        Estimate depth based on perspective:
        - Objects higher in frame = further away (for ground plane)
        - Detect vanishing points and horizon
        - Use Y-position as primary depth cue
        """
        depth = np.zeros_like(img_gray, dtype=np.float32)

        # Create vertical gradient (top = far, bottom = close)
        y_coords = np.linspace(0, 1, height)
        vertical_gradient = np.tile(y_coords[:, np.newaxis], (1, width))

        # Detect horizon line using edge detection
        edges = cv2.Canny(img_gray, 50, 150)

        # Use Hough Transform to find strong horizontal lines
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=50,
            minLineLength=width//4,
            maxLineGap=20
        )

        # Find horizon (strongest horizontal line in upper half)
        horizon_y = height * 0.4  # Default: 40% from top
        if lines is not None:
            horizontal_lines = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = abs(np.arctan2(y2 - y1, x2 - x1))
                # Check if line is horizontal (angle close to 0 or π)
                if angle < 0.2 or angle > (np.pi - 0.2):
                    if y1 < height * 0.6:  # In upper portion
                        horizontal_lines.append((y1 + y2) / 2)

            if horizontal_lines:
                horizon_y = np.median(horizontal_lines)

        # Adjust gradient based on horizon
        horizon_ratio = horizon_y / height

        # Create perspective depth map
        for y in range(height):
            if y < horizon_y:
                # Above horizon: linear falloff
                depth[y, :] = 1.0 - (y / horizon_y) * 0.5
            else:
                # Below horizon: stronger perspective
                depth[y, :] = 0.5 - ((y - horizon_y) / (height - horizon_y)) * 0.5

        return self._normalize(depth)

    def _edge_based_depth(self, img_gray):
        """
        Depth from edge structure:
        - Sharp edges = depth discontinuities = foreground/background boundaries
        - Edge density = object proximity
        - Canny + morphological operations
        """
        # Multi-scale edge detection
        edges1 = cv2.Canny(img_gray, 30, 90)
        edges2 = cv2.Canny(img_gray, 50, 150)
        edges3 = cv2.Canny(img_gray, 100, 200)

        # Combine edges
        edges = cv2.addWeighted(edges1, 0.3, edges2, 0.4, 0)
        edges = cv2.addWeighted(edges, 1.0, edges3, 0.3, 0)

        # Distance transform: distance from nearest edge
        # Farther from edges = flatter regions = often further away
        dist_transform = cv2.distanceTransform(
            255 - edges.astype(np.uint8),
            cv2.DIST_L2,
            5
        )

        # Invert and normalize
        depth = 1.0 - self._normalize(dist_transform)

        # Apply morphological closing to fill gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        depth = cv2.morphologyEx(depth, cv2.MORPH_CLOSE, kernel)

        return self._normalize(depth)

    def _atmospheric_depth(self, img_rgb, img_gray):
        """
        Depth from atmospheric perspective:
        - Distant objects are hazier, lower contrast, desaturated
        - Lighter/bluer tint for distant areas
        - Lower brightness variance = further
        """
        # Convert to HSV for saturation analysis
        img_hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        saturation = img_hsv[:, :, 1].astype(np.float32)
        value = img_hsv[:, :, 2].astype(np.float32)

        # Low saturation = far (desaturation with distance)
        saturation_depth = 1.0 - self._normalize(saturation)

        # Brightness/contrast analysis
        # Calculate local variance (contrast)
        kernel_size = 15
        mean = cv2.blur(img_gray.astype(np.float32), (kernel_size, kernel_size))
        mean_sq = cv2.blur(img_gray.astype(np.float32)**2, (kernel_size, kernel_size))
        variance = mean_sq - mean**2

        # Low contrast = far
        contrast_depth = 1.0 - self._normalize(variance)

        # Brightness: often darker or lighter in distance
        brightness = self._normalize(img_gray.astype(np.float32))

        # Combine atmospheric cues
        atmospheric = (saturation_depth * 0.4 +
                      contrast_depth * 0.4 +
                      brightness * 0.2)

        return self._normalize(atmospheric)

    def _texture_depth(self, img_gray):
        """
        Depth from texture/frequency analysis:
        - High frequency details = close objects
        - Low frequency = distant/blurred objects
        - FFT analysis of local patches
        """
        # Apply high-pass filter to detect fine details
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        high_freq = cv2.filter2D(img_gray.astype(np.float32), -1, kernel)
        high_freq = np.abs(high_freq)

        # Apply Laplacian for texture detail
        laplacian = cv2.Laplacian(img_gray, cv2.CV_64F)
        laplacian = np.abs(laplacian)

        # Gabor filter bank for texture analysis at multiple orientations
        texture_response = np.zeros_like(img_gray, dtype=np.float32)
        for theta in [0, np.pi/4, np.pi/2, 3*np.pi/4]:
            kernel = cv2.getGaborKernel(
                ksize=(21, 21),
                sigma=5,
                theta=theta,
                lambd=10,
                gamma=0.5,
                psi=0
            )
            filtered = cv2.filter2D(img_gray, cv2.CV_32F, kernel)
            texture_response += np.abs(filtered)

        # Combine texture cues
        texture_depth = (
            self._normalize(high_freq) * 0.3 +
            self._normalize(laplacian) * 0.3 +
            self._normalize(texture_response) * 0.4
        )

        # High texture = close
        return self._normalize(texture_depth)

    def _saliency_depth(self, img):
        """
        Depth from visual saliency:
        - Salient (attention-grabbing) regions are typically closer
        - Use spectral residual method
        """
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Resize for faster processing
        small = cv2.resize(gray, (256, 256))

        # Spectral Residual method
        # 1. Fourier transform
        fft = np.fft.fft2(small.astype(np.float32))
        magnitude = np.abs(fft)
        phase = np.angle(fft)

        # 2. Log spectrum
        log_magnitude = np.log(magnitude + 1)

        # 3. Spectral residual
        residual = log_magnitude - cv2.blur(log_magnitude, (3, 3))

        # 4. Inverse FFT
        saliency = np.abs(np.fft.ifft2(np.exp(residual + 1j * phase)))

        # Resize back to original size
        saliency = cv2.resize(saliency, (img.shape[1], img.shape[0]))

        # Smooth and normalize
        saliency = cv2.GaussianBlur(saliency, (11, 11), 0)

        # High saliency = closer
        return self._normalize(saliency)

    def _normalize(self, array):
        """Normalize array to 0-1 range"""
        array = array.astype(np.float32)
        min_val = array.min()
        max_val = array.max()
        if max_val > min_val:
            return (array - min_val) / (max_val - min_val)
        return array / 255.0 if max_val > 1 else array

    def _calculate_confidence(self, final_depth, individual_depths):
        """
        Calculate confidence map based on:
        - Agreement between different depth estimation methods
        - Gradient consistency
        - Edge alignment
        """
        # Measure agreement between methods (variance)
        depth_stack = np.stack(individual_depths, axis=0)
        variance = np.var(depth_stack, axis=0)

        # Low variance = high agreement = high confidence
        agreement_confidence = 1.0 - self._normalize(variance)

        # Gradient-based confidence (smooth regions = high confidence)
        grad_x = cv2.Sobel(final_depth, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(final_depth, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        gradient_confidence = 1.0 - self._normalize(gradient_magnitude)

        # Combine confidences
        confidence_map = (agreement_confidence * 0.6 +
                         gradient_confidence * 0.4)

        # Smooth confidence map
        confidence_map = cv2.GaussianBlur(confidence_map.astype(np.float32), (7, 7), 0)

        return self._normalize(confidence_map)

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
