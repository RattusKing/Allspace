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
            # Load image (match depth map dimensions for vertex color fallback)
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Resize image to match depth map dimensions
            dh, dw = depth_map.shape
            if image.shape[:2] != (dh, dw):
                image = cv2.resize(image, (dw, dh), interpolation=cv2.INTER_LANCZOS4)

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
                # Use UV-textured heightmap mesh for photos
                print("  📸 Photo mode - using heightmap mesh with UV texture")
                mesh = self._depth_to_mesh(
                    depth_map,
                    image,
                    width,
                    height,
                    confidence_map,
                    image_path=image_path
                )

            print(f"✅ Generated base mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")

            return mesh, image_data

        except Exception as e:
            print(f"❌ Error creating mesh: {e}")
            raise

    def _depth_to_mesh(self, depth_map, image, width, height, confidence_map=None,
                       image_path=None):
        """
        Convert depth map to a UV-textured 3D heightmap mesh.

        Uses the original full-resolution image as a texture for maximum fidelity,
        with UV coordinates that map each vertex to the correct pixel.

        Args:
            depth_map: 2D depth values
            image: RGB image (potentially downsampled)
            width, height: Image dimensions
            confidence_map: Optional confidence values
            image_path: Path to original image for high-quality texture

        Returns:
            mesh: Trimesh object with UV texture or vertex colors
        """
        # Determine target mesh resolution (stay under 512MB)
        max_dimension = max(width, height)
        if max_dimension > 512:
            target_w = int(width * 512 / max_dimension)
            target_h = int(height * 512 / max_dimension)
        else:
            target_w, target_h = width, height

        if target_w != width or target_h != height:
            print(f"  🔽 Downsampling mesh {width}x{height} → {target_w}x{target_h} (INTER_AREA)")
            # INTER_AREA averages pixels correctly (no aliasing vs stride slicing)
            depth_map = cv2.resize(depth_map, (target_w, target_h),
                                   interpolation=cv2.INTER_AREA)
            image = cv2.resize(image, (target_w, target_h),
                               interpolation=cv2.INTER_AREA)
            if confidence_map is not None:
                confidence_map = cv2.resize(confidence_map, (target_w, target_h),
                                            interpolation=cv2.INTER_AREA)
            width, height = target_w, target_h

        print(f"  ✅ Mesh resolution: {width}x{height} = {width * height} vertices")

        # Pre-process depth: bilateral filter smooths flat regions while
        # keeping hard depth edges (object boundaries) sharp
        depth_smooth = cv2.bilateralFilter(
            depth_map.astype(np.float32), d=7, sigmaColor=0.05, sigmaSpace=7
        )

        # Stronger depth scale for clearly visible 3D effect
        depth_scale = 1.5

        # Build vertex positions on a regular grid
        # Coordinate system: X=right, Y=up (from image), Z=depth
        x = np.arange(0, width, dtype=np.float32)
        y = np.arange(0, height, dtype=np.float32)
        x_grid, y_grid = np.meshgrid(x, y)

        x_norm = (x_grid - width / 2.0) / (width / 2.0)   # -1 to 1
        y_norm = (y_grid - height / 2.0) / (height / 2.0)  # -1 to 1

        z = depth_smooth * depth_scale

        # Stack into Nx3 vertex array (Y-up: flip image Y so top→positive)
        vertices = np.stack([
            x_norm.flatten(),
            -y_norm.flatten(),   # flip: image row 0 = top = +Y in 3D
            z.flatten()
        ], axis=1).astype(np.float32)

        # UV coordinates (u=0..1 left→right, v=0..1 top→bottom for image space)
        u = (x_grid / (width - 1)).flatten().astype(np.float32)
        v = (y_grid / (height - 1)).flatten().astype(np.float32)
        uv_coords = np.stack([u, 1.0 - v], axis=1)  # flip V for OpenGL convention

        # Build face index array vectorised (much faster than Python loop)
        row_idx = np.arange(height - 1)
        col_idx = np.arange(width - 1)
        rr, cc = np.meshgrid(row_idx, col_idx, indexing='ij')
        v0 = (rr * width + cc).flatten()
        v1 = v0 + 1
        v2 = v0 + width
        v3 = v0 + width + 1
        # Two triangles per quad (counter-clockwise winding, Y-up)
        faces = np.concatenate([
            np.stack([v0, v1, v2], axis=1),
            np.stack([v1, v3, v2], axis=1)
        ], axis=0).astype(np.int32)

        # Try to build a UV-textured mesh using the original full-res image
        # so the texture exactly matches the 2D source photo.
        mesh = None
        if image_path is not None:
            try:
                from PIL import Image as PILImage
                pil_img = PILImage.open(image_path).convert("RGB")
                material = trimesh.visual.material.SimpleMaterial(image=pil_img)
                texture_visuals = trimesh.visual.TextureVisuals(
                    uv=uv_coords,
                    material=material
                )
                mesh = trimesh.Trimesh(
                    vertices=vertices,
                    faces=faces,
                    visual=texture_visuals,
                    process=False  # Keep vertex order for UV correctness
                )
                print("  🖼️  UV-textured mesh created from original image")
            except Exception as tex_err:
                print(f"  ⚠️  UV texture failed ({tex_err}), falling back to vertex colors")
                mesh = None

        if mesh is None:
            # Fallback: vertex colors (still higher quality with INTER_AREA downsampling)
            vertex_colors = image.reshape(-1, 3)
            mesh = trimesh.Trimesh(
                vertices=vertices,
                faces=faces,
                vertex_colors=vertex_colors,
                process=True
            )
            print("  🎨 Vertex-colored mesh created")

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
        # Downsample moderately to preserve architectural detail
        # Use INTER_AREA for correct area-averaging (no stride aliasing)
        max_dimension = max(width, height)

        if max_dimension > 800:
            target_dim = 640
            tw = int(width * target_dim / max_dimension)
            th = int(height * target_dim / max_dimension)
            print(f"  🔽 Downsampling for wall detection: {width}x{height} → {tw}x{th} (INTER_AREA)")
            depth_map_small = cv2.resize(depth_map, (tw, th), interpolation=cv2.INTER_AREA)
            image_small = cv2.resize(image, (tw, th), interpolation=cv2.INTER_AREA)
            h_small, w_small = th, tw
        else:
            print(f"  ✅ Using full resolution: {width}x{height} for maximum architectural detail")
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
        wall_thickness = 0.05  # Slight wall thickness for realism
        print(f"  📐 Using Y-up orientation: Floor=XZ plane (Y={floor_height}), Walls=+Y direction (ceiling Y={ceiling_height})")
        print(f"  🏗️  Architectural detail: Wall thickness={wall_thickness}, preserving floor plan geometry")

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

        for contour_idx, contour in enumerate(contours):
            # Skip tiny contours (noise/text)
            if len(contour) < 4:
                continue

            # Less aggressive contour approximation to preserve architectural detail
            # Architects need precision - use smaller epsilon
            epsilon = 0.002 * cv2.arcLength(contour, True)  # Much more precise (was 0.01)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if len(approx) < 3:
                continue

            # Sample wall color from floor plan image at contour location
            # Use median color along the contour for realistic appearance
            contour_colors = []
            for point in approx:
                px, py = point[0]
                if 0 <= py < h_small and 0 <= px < w_small:
                    color = image_small[py, px]
                    contour_colors.append(color)

            if len(contour_colors) > 0:
                # Use median color for this wall segment
                wall_color = np.median(contour_colors, axis=0).astype(np.uint8).tolist()
            else:
                # Fallback to neutral gray
                wall_color = [120, 120, 120]

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
        floor_color = [220, 220, 220]  # Light gray floor

        vertices.extend(floor_vertices)
        colors.extend([floor_color] * 4)

        # Floor faces (2 triangles) - order matters for proper normal direction
        base_idx = vertex_offset
        faces.append([base_idx, base_idx + 1, base_idx + 2])
        faces.append([base_idx, base_idx + 2, base_idx + 3])
        vertex_offset += 4

        # Create ceiling plane (horizontal XZ plane at Y=ceiling_height)
        # Professional architectural viz typically shows ceiling
        ceiling_vertices = [
            [-1.0, ceiling_height, -1.0],  # X, Y, Z
            [1.0, ceiling_height, -1.0],
            [1.0, ceiling_height, 1.0],
            [-1.0, ceiling_height, 1.0]
        ]
        ceiling_color = [240, 240, 240]  # Very light gray ceiling

        vertices.extend(ceiling_vertices)
        colors.extend([ceiling_color] * 4)

        # Ceiling faces (2 triangles) - reversed winding for downward-facing normals
        base_idx = vertex_offset
        faces.append([base_idx, base_idx + 2, base_idx + 1])
        faces.append([base_idx, base_idx + 3, base_idx + 2])

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
