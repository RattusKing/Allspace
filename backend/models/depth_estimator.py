"""
Depth Estimation Module
Uses MiDaS or Depth Anything for monocular depth estimation
"""

import cv2
import numpy as np
import torch
from PIL import Image


class DepthEstimator:
    """Estimates depth from 2D images using pre-trained models"""

    def __init__(self, model_type='MiDaS_small'):
        """
        Initialize depth estimation model (lazy loading)

        Args:
            model_type: 'MiDaS_small' (faster, less accurate) or 'DPT_Large' (slower, more accurate)
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_type = model_type
        self.model = None
        self.transform = None
        print(f"🔧 Depth Estimator ready (model will load on first use)")

    def _ensure_model_loaded(self):
        """Lazy load the model only when needed to save startup memory"""
        if self.model is not None:
            return  # Already loaded

        print(f"📥 Loading MiDaS model (first time, ~100MB download)...")
        try:
            # Load MiDaS model - using small version for Render free tier
            self.model = torch.hub.load('intel-isl/MiDaS', self.model_type, pretrained=True, trust_repo=True)
            self.model.to(self.device)
            self.model.eval()

            # Load transforms
            midas_transforms = torch.hub.load('intel-isl/MiDaS', 'transforms', trust_repo=True)
            if self.model_type == 'DPT_Large' or self.model_type == 'DPT_Hybrid':
                self.transform = midas_transforms.dpt_transform
            else:
                self.transform = midas_transforms.small_transform

            print(f"✅ Depth model loaded: {self.model_type}")

        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise

    def estimate_depth(self, image_path):
        """
        Estimate depth map from image

        Args:
            image_path: Path to input image

        Returns:
            depth_map: Normalized depth map (numpy array)
            confidence_map: Confidence/uncertainty map
        """
        # Lazy load model on first use
        self._ensure_model_loaded()

        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not load image: {image_path}")

            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Apply transforms
            input_batch = self.transform(img).to(self.device)

            # Predict depth
            with torch.no_grad():
                prediction = self.model(input_batch)
                prediction = torch.nn.functional.interpolate(
                    prediction.unsqueeze(1),
                    size=img.shape[:2],
                    mode='bicubic',
                    align_corners=False
                ).squeeze()

            depth_map = prediction.cpu().numpy()

            # Normalize depth map to 0-1 range
            depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())

            # Invert so closer = higher values (standard convention)
            depth_map = 1.0 - depth_map

            # Calculate confidence map based on depth gradient
            # Areas with high gradient change might be less confident
            confidence_map = self._calculate_confidence(depth_map)

            return depth_map, confidence_map

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

    def estimate_scale_and_focal_length(self, image_shape, depth_map):
        """
        Estimate reasonable scale and focal length for 3D projection

        Args:
            image_shape: (height, width) of image
            depth_map: Estimated depth map

        Returns:
            focal_length, scale_factor
        """
        height, width = image_shape[:2]

        # Estimate focal length based on image size (rough approximation)
        # Typical FOV for photos is around 60-70 degrees
        focal_length = width * 0.8

        # Estimate scale to get reasonable 3D coordinates
        # Adjust based on depth variation
        depth_range = depth_map.max() - depth_map.min()
        scale_factor = 10.0 / max(depth_range, 0.01)  # Scale to ~10 units depth range

        return focal_length, scale_factor
