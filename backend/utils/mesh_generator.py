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

            # Detect if this is a floor plan (bimodal depth distribution)
            low_depth = np.sum((depth_map >= 0.0) & (depth_map < 0.2)) / depth_map.size
            high_depth = np.sum((depth_map >= 0.8) & (depth_map <= 1.0)) / depth_map.size
            is_floor_plan = (low_depth + high_depth) > 0.6

            if is_floor_plan:
                # Use architectural mesh generation (wall extrusion)
                print("  🏗️  Floor plan detected - using architectural wall extrusion")
                mesh = self._architectural_mesh(
                    depth_map,
                    image,
                    width,
                    height
                )
            else:
                # Use traditional heightmap mesh generation
                print("  📸 Photo mode - using heightmap mesh generation")
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

        # Create 3D heightmap mesh for photos
        # (Floor plans use _architectural_mesh instead)

        # Normalize coordinates to -1 to 1 range for clean positioning
        x_normalized = (x_grid - width / 2.0) / (width / 2.0)
        y_normalized = (y_grid - height / 2.0) / (height / 2.0)

        # Moderate depth scale for photo-realistic 3D
        depth_scale = 0.8

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

    def _architectural_mesh(self, depth_map, image, width, height):
        """
        Create architectural 3D mesh with proper wall extrusion
        Walls are vertical faces, floors are horizontal planes

        Args:
            depth_map: Binary-like depth (0=floor, 1=wall)
            image: RGB image for colors
            width, height: Dimensions

        Returns:
            mesh: Trimesh object with architectural geometry
        """
        # Downsample to reduce vertex count (memory optimization)
        downsample_factor = 1
        max_dimension = max(width, height)

        if max_dimension > 256:
            downsample_factor = 2  # 640→320, but we want even less for walls
        if max_dimension > 512:
            downsample_factor = 4  # 640→160 for wall detection

        if downsample_factor > 1:
            print(f"  🔽 Downsampling for wall detection: {width}x{height} → {width//downsample_factor}x{height//downsample_factor}")
            depth_map_small = depth_map[::downsample_factor, ::downsample_factor]
            image_small = image[::downsample_factor, ::downsample_factor]
            h_small, w_small = depth_map_small.shape
        else:
            depth_map_small = depth_map
            image_small = image
            h_small, w_small = height, width

        # Create binary wall mask (walls = high depth)
        wall_mask = (depth_map_small > 0.5).astype(np.uint8) * 255

        # Find contours of wall regions
        contours, hierarchy = cv2.findContours(wall_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

        print(f"  🔍 Found {len(contours)} wall contours")

        # Architectural parameters
        # Use Y-up coordinate system (industry standard)
        # Floor plan in XZ plane (horizontal), walls extrude in +Y (upward)
        ceiling_height = 2.5  # Units in 3D space (represents 8-10 feet)
        floor_height = 0.0
        print(f"  📐 Using Y-up orientation: Floor=XZ plane (Y={floor_height}), Walls=+Y direction (ceiling Y={ceiling_height})")

        # Normalize coordinates to -1 to 1 range
        scale_x = 2.0 / w_small
        scale_z = 2.0 / h_small  # Changed from scale_y - this is now depth (Z)
        offset_x = -1.0
        offset_z = -1.0  # Changed from offset_y

        vertices = []
        faces = []
        colors = []

        # Process each contour (outer walls and inner walls)
        vertex_offset = 0
        wall_color = [100, 100, 100]  # Gray walls

        for contour_idx, contour in enumerate(contours):
            # Skip tiny contours (noise/text)
            if len(contour) < 4:
                continue

            # Approximate contour to reduce vertex count
            epsilon = 0.01 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if len(approx) < 3:
                continue

            # Create vertical wall faces along contour
            for i in range(len(approx)):
                p1 = approx[i][0]
                p2 = approx[(i + 1) % len(approx)][0]

                # Convert pixel coordinates to normalized 3D coordinates
                # Floor plan is in XZ plane (horizontal), walls extrude in +Y (up)
                x1 = p1[0] * scale_x + offset_x
                z1 = -(p1[1] * scale_z + offset_z)  # Image Y → 3D Z (depth), flipped
                x2 = p2[0] * scale_x + offset_x
                z2 = -(p2[1] * scale_z + offset_z)  # Image Y → 3D Z (depth), flipped

                # Create 4 vertices for this wall segment (rectangular face)
                # Bottom edge (floor level, Y=0)
                v0 = [x1, floor_height, z1]  # X, Y, Z
                v1 = [x2, floor_height, z2]
                # Top edge (ceiling level, Y=2.5)
                v2 = [x2, ceiling_height, z2]
                v3 = [x1, ceiling_height, z1]

                vertices.extend([v0, v1, v2, v3])
                colors.extend([wall_color] * 4)

                # Create 2 triangles for this rectangular wall face
                base_idx = vertex_offset
                faces.append([base_idx, base_idx + 1, base_idx + 2])
                faces.append([base_idx, base_idx + 2, base_idx + 3])

                vertex_offset += 4

        # Create floor plane (horizontal XZ plane at Y=0)
        floor_vertices = [
            [-1.0, floor_height, -1.0],  # X, Y, Z
            [1.0, floor_height, -1.0],
            [1.0, floor_height, 1.0],
            [-1.0, floor_height, 1.0]
        ]
        floor_color = [200, 200, 200]  # Light gray floor

        vertices.extend(floor_vertices)
        colors.extend([floor_color] * 4)

        # Floor faces (2 triangles) - order matters for proper normal direction
        base_idx = vertex_offset
        faces.append([base_idx, base_idx + 1, base_idx + 2])
        faces.append([base_idx, base_idx + 2, base_idx + 3])

        if len(vertices) == 0:
            print("  ⚠️  No wall geometry generated, creating simple box")
            # Fallback: create a simple box
            return self._create_fallback_box()

        vertices = np.array(vertices, dtype=np.float32)
        faces = np.array(faces, dtype=np.int32)
        colors = np.array(colors, dtype=np.uint8)

        print(f"  ✅ Generated {len(vertices)} vertices, {len(faces)} faces for architectural mesh")

        # Create trimesh
        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=faces,
            vertex_colors=colors,
            process=True
        )

        return mesh

    def _create_fallback_box(self):
        """Create a simple box as fallback"""
        box = trimesh.creation.box(extents=[2.0, 2.0, 0.5])
        return box

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
