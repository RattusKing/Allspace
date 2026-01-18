"""
Mesh Generation Module
Creates 3D meshes from depth maps and images using trimesh (no Open3D required)
"""

import numpy as np
import cv2
import trimesh
from scipy.spatial import Delaunay
from PIL import Image


class MeshGenerator:
    """Generates 3D meshes from 2D images and depth maps"""

    def __init__(self):
        print("🔧 Initializing Mesh Generator (trimesh-based)")

    def create_mesh_from_depth(self, image_path, depth_map, confidence_map=None):
        """
        Create a 3D mesh from image and depth map

        Args:
            image_path: Path to original image
            depth_map: Depth values for each pixel
            confidence_map: Optional confidence values

        Returns:
            mesh: Trimesh object
            image_data: Original image data for texturing
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_data = image.copy()

            height, width = depth_map.shape

            # Create mesh directly from depth map
            mesh = self._depth_to_mesh(
                depth_map,
                image,
                width,
                height,
                confidence_map
            )

            print(f"✅ Generated base mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")

            return mesh, image_data

        except Exception as e:
            print(f"❌ Error creating mesh: {e}")
            raise

    def _depth_to_mesh(self, depth_map, image, width, height, confidence_map=None):
        """
        Convert depth map directly to mesh using trimesh

        Args:
            depth_map: 2D depth values
            image: RGB image
            width, height: Image dimensions
            confidence_map: Optional confidence values

        Returns:
            mesh: Trimesh object
        """
        # Aggressive downsampling to stay under 512MB memory limit
        # Target: ~100K vertices max (320x320 = 102,400)
        downsample_factor = 1
        max_dimension = max(width, height)

        if max_dimension > 512:
            downsample_factor = 2  # 640x640 → 320x320
        if max_dimension > 1024:
            downsample_factor = 4  # 1280x1280 → 320x320

        if downsample_factor > 1:
            print(f"  🔽 Downsampling mesh from {width}x{height} by factor {downsample_factor} to reduce memory usage")
            depth_map = depth_map[::downsample_factor, ::downsample_factor]
            image = image[::downsample_factor, ::downsample_factor]
            if confidence_map is not None:
                confidence_map = confidence_map[::downsample_factor, ::downsample_factor]
            height, width = depth_map.shape
            print(f"  ✅ Mesh resolution: {width}x{height} = {width * height} vertices")

        # Create coordinate grids
        x = np.arange(0, width)
        y = np.arange(0, height)
        x_grid, y_grid = np.meshgrid(x, y)

        # Create 3D mesh optimized for architectural floor plans
        # Also works for photos with increased depth effect

        # Normalize coordinates to -1 to 1 range for clean positioning
        x_normalized = (x_grid - width / 2.0) / (width / 2.0)
        y_normalized = (y_grid - height / 2.0) / (height / 2.0)

        # Detect if this is a floor plan (bimodal depth distribution)
        # Floor plans have lots of 0s (floors) and 1s (walls), not much in between
        low_depth = np.sum((depth_map >= 0.0) & (depth_map < 0.2)) / depth_map.size
        high_depth = np.sum((depth_map >= 0.8) & (depth_map <= 1.0)) / depth_map.size
        is_floor_plan = (low_depth + high_depth) > 0.6  # 60%+ is either floor or wall

        if is_floor_plan:
            # Higher depth scale for architectural visualization
            # Represents 8-10 foot ceiling height
            depth_scale = 1.8
            print(f"  🏗️  Architectural mode: Using depth scale {depth_scale} for room height")
        else:
            # Moderate depth scale for photo-realistic 3D
            depth_scale = 0.8
            print(f"  📸 Photo mode: Using depth scale {depth_scale} for subtle 3D effect")

        # Apply depth (positive Z = above grid, not under it!)
        z = depth_map * depth_scale

        # Create flat plane coordinates
        x_3d = x_normalized
        y_3d = y_normalized

        # Flatten arrays (Z is POSITIVE for above grid)
        vertices = np.stack([x_3d.flatten(), -y_3d.flatten(), z.flatten()], axis=1)

        # Get colors from image
        vertex_colors = image.reshape(-1, 3)

        # Disable confidence filtering for now - it causes face generation bugs
        # Just use all vertices

        # Create grid triangulation directly
        faces = []

        # Create faces from grid (every quad becomes 2 triangles)
        for i in range(height - 1):
            for j in range(width - 1):
                # Current vertex index
                idx = i * width + j

                # Indices of the quad's 4 corners
                v0 = idx
                v1 = idx + 1
                v2 = idx + width
                v3 = idx + width + 1

                # Create two triangles for this quad
                faces.append([v0, v1, v2])
                faces.append([v1, v3, v2])

        faces = np.array(faces, dtype=np.int32)

        # Create trimesh object
        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=faces,
            vertex_colors=vertex_colors,
            process=True  # Auto-process: validates, removes degenerates, merges vertices
        )

        # Mesh is already cleaned by process=True
        return mesh

    def create_textured_mesh(self, mesh, image_data):
        """
        Apply texture to mesh using image (trimesh already has vertex colors)

        Args:
            mesh: Trimesh object
            image_data: RGB image

        Returns:
            mesh: Textured mesh
        """
        # Trimesh already handles vertex colors well
        return mesh

    def subdivide_mesh(self, mesh, iterations=1):
        """
        Subdivide mesh for smoother surface

        Args:
            mesh: Input trimesh
            iterations: Number of subdivision iterations

        Returns:
            subdivided_mesh
        """
        for _ in range(iterations):
            mesh = mesh.subdivide()

        return mesh

    def smooth_mesh(self, mesh, iterations=1):
        """
        Apply Laplacian smoothing to mesh

        Args:
            mesh: Input trimesh
            iterations: Number of smoothing iterations

        Returns:
            smoothed_mesh
        """
        # Trimesh doesn't have built-in Laplacian smoothing
        # We can approximate it by averaging vertex positions
        for _ in range(iterations):
            vertices = mesh.vertices.copy()
            vertex_neighbors = mesh.vertex_neighbors
            
            for i, neighbors in enumerate(vertex_neighbors):
                if len(neighbors) > 0:
                    vertices[i] = np.mean(mesh.vertices[neighbors], axis=0)
            
            mesh.vertices = vertices

        # Normals are automatically recomputed by trimesh when accessed
        return mesh
