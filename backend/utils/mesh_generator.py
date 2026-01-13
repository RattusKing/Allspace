"""
Mesh Generation Module
Creates 3D meshes from depth maps and images
"""

import numpy as np
import cv2
import open3d as o3d
from PIL import Image


class MeshGenerator:
    """Generates 3D meshes from 2D images and depth maps"""

    def __init__(self):
        print("🔧 Initializing Mesh Generator")

    def create_mesh_from_depth(self, image_path, depth_map, confidence_map=None):
        """
        Create a 3D mesh from image and depth map

        Args:
            image_path: Path to original image
            depth_map: Depth values for each pixel
            confidence_map: Optional confidence values

        Returns:
            mesh: Open3D TriangleMesh object
            image_data: Original image data for texturing
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_data = image.copy()

            height, width = depth_map.shape

            # Create point cloud from depth map
            point_cloud = self._depth_to_point_cloud(
                depth_map,
                image,
                width,
                height,
                confidence_map
            )

            # Convert to mesh
            mesh = self._point_cloud_to_mesh(point_cloud)

            print(f"✅ Generated base mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")

            return mesh, image_data

        except Exception as e:
            print(f"❌ Error creating mesh: {e}")
            raise

    def _depth_to_point_cloud(self, depth_map, image, width, height, confidence_map=None):
        """
        Convert depth map to 3D point cloud

        Args:
            depth_map: 2D depth values
            image: RGB image
            width, height: Image dimensions
            confidence_map: Optional confidence values

        Returns:
            point_cloud: Open3D PointCloud object
        """
        # Create coordinate grids
        x = np.linspace(0, width - 1, width)
        y = np.linspace(0, height - 1, height)
        x_grid, y_grid = np.meshgrid(x, y)

        # Estimate focal length (rough approximation)
        focal_length = width * 0.8

        # Center coordinates
        cx = width / 2.0
        cy = height / 2.0

        # Scale depth for better visualization
        depth_scale = 5.0  # Adjust this for depth effect

        # Convert to 3D coordinates
        z = depth_map * depth_scale
        x_3d = (x_grid - cx) * z / focal_length
        y_3d = (y_grid - cy) * z / focal_length

        # Flatten arrays
        points = np.stack([x_3d.flatten(), -y_3d.flatten(), -z.flatten()], axis=1)

        # Get colors from image
        colors = image.reshape(-1, 3) / 255.0

        # Filter points by confidence if available
        if confidence_map is not None:
            confidence_threshold = 0.3
            valid_mask = confidence_map.flatten() > confidence_threshold
            points = points[valid_mask]
            colors = colors[valid_mask]

        # Create Open3D point cloud
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        pcd.colors = o3d.utility.Vector3dVector(colors)

        # Remove outliers
        pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)

        # Estimate normals
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30)
        )

        return pcd

    def _point_cloud_to_mesh(self, point_cloud):
        """
        Convert point cloud to triangle mesh

        Args:
            point_cloud: Open3D PointCloud

        Returns:
            mesh: Open3D TriangleMesh
        """
        # Use Poisson surface reconstruction
        try:
            mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                point_cloud,
                depth=9,
                width=0,
                scale=1.1,
                linear_fit=False
            )

            # Remove low-density vertices
            vertices_to_remove = densities < np.quantile(densities, 0.01)
            mesh.remove_vertices_by_mask(vertices_to_remove)

        except Exception as e:
            print(f"⚠️  Poisson reconstruction failed, using ball pivoting: {e}")
            # Fallback to ball pivoting if Poisson fails
            distances = point_cloud.compute_nearest_neighbor_distance()
            avg_dist = np.mean(distances)
            radius = 3 * avg_dist
            mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
                point_cloud,
                o3d.utility.DoubleVector([radius, radius * 2])
            )

        # Clean up mesh
        mesh.remove_duplicated_vertices()
        mesh.remove_duplicated_triangles()
        mesh.remove_degenerate_triangles()
        mesh.remove_unreferenced_vertices()

        # Compute vertex normals
        mesh.compute_vertex_normals()

        return mesh

    def create_textured_mesh(self, mesh, image_data):
        """
        Apply texture to mesh using image

        Args:
            mesh: Open3D TriangleMesh
            image_data: RGB image

        Returns:
            mesh: Textured mesh
        """
        try:
            # For now, we'll use vertex colors
            # Full UV mapping would require more complex projection
            if not mesh.has_vertex_colors():
                # Use existing colors from point cloud or generate from normals
                if not mesh.has_vertex_normals():
                    mesh.compute_vertex_normals()

            return mesh

        except Exception as e:
            print(f"⚠️  Error texturing mesh: {e}")
            return mesh

    def subdivide_mesh(self, mesh, iterations=1):
        """
        Subdivide mesh for smoother surface

        Args:
            mesh: Input mesh
            iterations: Number of subdivision iterations

        Returns:
            subdivided_mesh
        """
        for _ in range(iterations):
            mesh = mesh.subdivide_midpoint(number_of_iterations=1)

        return mesh

    def smooth_mesh(self, mesh, iterations=1):
        """
        Apply Laplacian smoothing to mesh

        Args:
            mesh: Input mesh
            iterations: Number of smoothing iterations

        Returns:
            smoothed_mesh
        """
        mesh = mesh.filter_smooth_simple(number_of_iterations=iterations)
        mesh.compute_vertex_normals()

        return mesh
