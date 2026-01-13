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
        # Downsample for performance (optional)
        downsample_factor = 1
        if width > 1024 or height > 1024:
            downsample_factor = 2
        
        if downsample_factor > 1:
            depth_map = depth_map[::downsample_factor, ::downsample_factor]
            image = image[::downsample_factor, ::downsample_factor]
            if confidence_map is not None:
                confidence_map = confidence_map[::downsample_factor, ::downsample_factor]
            height, width = depth_map.shape

        # Create coordinate grids
        x = np.arange(0, width)
        y = np.arange(0, height)
        x_grid, y_grid = np.meshgrid(x, y)

        # Estimate focal length (rough approximation)
        focal_length = width * 0.8

        # Center coordinates
        cx = width / 2.0
        cy = height / 2.0

        # Scale depth for better visualization
        depth_scale = 5.0

        # Convert to 3D coordinates
        z = depth_map * depth_scale
        x_3d = (x_grid - cx) * z / focal_length
        y_3d = (y_grid - cy) * z / focal_length

        # Flatten arrays
        vertices = np.stack([x_3d.flatten(), -y_3d.flatten(), -z.flatten()], axis=1)

        # Get colors from image
        vertex_colors = image.reshape(-1, 3)

        # Filter by confidence if available
        if confidence_map is not None:
            confidence_threshold = 0.3
            valid_mask = confidence_map.flatten() > confidence_threshold
            # Keep indices for reconstruction
            valid_indices = np.where(valid_mask)[0]
        else:
            valid_indices = np.arange(len(vertices))

        # Create grid triangulation
        faces = []
        vertex_map = np.full(height * width, -1, dtype=int)
        vertex_map[valid_indices] = np.arange(len(valid_indices))

        filtered_vertices = vertices[valid_indices]
        filtered_colors = vertex_colors[valid_indices]

        # Create faces from grid
        for i in range(height - 1):
            for j in range(width - 1):
                idx = i * width + j
                
                if confidence_map is not None:
                    # Check if all vertices are valid
                    if (vertex_map[idx] < 0 or 
                        vertex_map[idx + 1] < 0 or 
                        vertex_map[idx + width] < 0 or
                        vertex_map[idx + width + 1] < 0):
                        continue
                
                v0 = vertex_map[idx] if confidence_map is not None else idx
                v1 = vertex_map[idx + 1] if confidence_map is not None else idx + 1
                v2 = vertex_map[idx + width] if confidence_map is not None else idx + width
                v3 = vertex_map[idx + width + 1] if confidence_map is not None else idx + width + 1

                # Create two triangles for this quad
                faces.append([v0, v1, v2])
                faces.append([v1, v3, v2])

        faces = np.array(faces)
        
        if confidence_map is not None:
            vertices = filtered_vertices
            vertex_colors = filtered_colors

        # Remove degenerate faces (faces where vertices are too close)
        if len(faces) > 0:
            # Calculate face areas
            v0 = vertices[faces[:, 0]]
            v1 = vertices[faces[:, 1]]
            v2 = vertices[faces[:, 2]]
            
            # Cross product to get face normals and areas
            cross = np.cross(v1 - v0, v2 - v0)
            areas = np.linalg.norm(cross, axis=1)
            
            # Keep faces with reasonable area
            valid_faces = areas > 0.001
            faces = faces[valid_faces]

        # Create trimesh object
        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=faces,
            vertex_colors=vertex_colors,
            process=False  # Don't auto-process, we'll do it manually
        )

        # Clean up mesh
        mesh.remove_duplicate_faces()
        mesh.remove_degenerate_faces()
        mesh.remove_unreferenced_vertices()
        
        # Fix normals
        mesh.fix_normals()

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

        mesh.fix_normals()
        return mesh
