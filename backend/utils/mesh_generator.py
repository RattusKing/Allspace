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

    def create_mesh_from_depth(self, image_path, depth_map, confidence_map=None,
                               scene_type=None, scale_factor_x=1.0, scale_factor_z=1.0,
                               complexity="medium", generate_interiors=True):
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

            # Choose mesh strategy based on scene type (or fall back to heuristic)
            if scene_type == "building_facade":
                print("  🏠 Building facade - creating extruded box model")
                mesh = self._facade_box_mesh(
                    depth_map, image, width, height, image_path=image_path
                )
            elif scene_type == "floor_plan":
                print("  🏗️  Floor plan - using architectural wall extrusion")
                mesh = self._architectural_mesh(depth_map, image, width, height,
                                                scale_factor_x=scale_factor_x,
                                                scale_factor_z=scale_factor_z,
                                                complexity=complexity,
                                                generate_interiors=generate_interiors)
            else:
                # Heuristic fallback for scenes whose type isn't propagated
                low_depth  = np.sum((depth_map >= 0.0) & (depth_map < 0.2)) / depth_map.size
                high_depth = np.sum((depth_map >= 0.8) & (depth_map <= 1.0)) / depth_map.size
                if (low_depth + high_depth) > 0.6:
                    print("  🏗️  Floor plan heuristic - architectural wall extrusion")
                    mesh = self._architectural_mesh(depth_map, image, width, height,
                                                    scale_factor_x=scale_factor_x,
                                                    scale_factor_z=scale_factor_z,
                                                    complexity=complexity,
                                                    generate_interiors=generate_interiors)
                else:
                    print("  📸 Photo mode - heightmap mesh with UV texture")
                    mesh = self._depth_to_mesh(
                        depth_map, image, width, height, confidence_map,
                        image_path=image_path
                    )

            if isinstance(mesh, trimesh.Scene):
                total_v = sum(len(g.vertices) for g in mesh.geometry.values())
                total_f = sum(len(g.faces)    for g in mesh.geometry.values())
                print(f"✅ Generated facade scene: {len(mesh.geometry)} meshes, "
                      f"{total_v} vertices, {total_f} faces")
            else:
                print(f"✅ Generated base mesh: {len(mesh.vertices)} vertices, "
                      f"{len(mesh.faces)} faces")

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

    def _facade_box_mesh(self, depth_map, image, width, height, image_path=None):
        """
        Create a proper 3D box model for building facade / elevation images.

        Returns a trimesh.Scene (not a single Trimesh) so different materials
        survive GLB export without concatenation stripping the UV texture:

          • front_face  – dense grid, UV-textured from the original image
                          (every window/door/colour detail is preserved)
          • left_wall / right_wall – vertex-coloured quads, edge-sampled colour
          • roof_slab   – vertex-coloured quad
          • back_wall   – vertex-coloured quad
          • ground_plane – vertex-coloured quad, extends in front of building
        """
        # ── Sky / ground boundaries from depth map ────────────────────────
        row_depth    = np.mean(depth_map, axis=1)
        sky_end      = 0
        for r in range(height):
            if row_depth[r] > 0.20:
                sky_end = r
                break
        ground_start = height - 1
        for r in range(height - 1, height // 2, -1):
            if row_depth[r] < 0.55:
                ground_start = r
                break

        sky_end      = min(sky_end,      int(height * 0.35))
        ground_start = max(ground_start, int(height * 0.65))

        # ── World-space layout ─────────────────────────────────────────────
        aspect     = height / max(width, 1)
        face_w     = 2.0
        face_h     = 2.0 * aspect
        building_d = max(0.6, face_w * 0.45)

        sky_uv    = sky_end      / height
        ground_uv = ground_start / height
        roof_y    =  face_h / 2.0 - sky_uv    * face_h
        ground_y  =  face_h / 2.0 - ground_uv * face_h
        xl = -face_w / 2.0
        xr =  face_w / 2.0

        # ── Edge colour sampling ───────────────────────────────────────────
        def edge_mean(img, rows_slice, cols_slice):
            region = img[rows_slice, cols_slice]
            if region.size == 0:
                return np.array([180, 170, 150], dtype=np.uint8)
            return np.mean(region.reshape(-1, 3), axis=0).astype(np.uint8)

        wall_color   = edge_mean(image, slice(sky_end, ground_start), slice(0, width))
        left_color   = edge_mean(image, slice(sky_end, ground_start),
                                 slice(0, max(1, width // 15)))
        right_color  = edge_mean(image, slice(sky_end, ground_start),
                                 slice(max(0, width - width // 15), width))
        roof_color   = edge_mean(image, slice(max(0, sky_end - 8), sky_end + 4),
                                 slice(0, width))
        ground_color = edge_mean(image,
                                 slice(ground_start, min(height, ground_start + 10)),
                                 slice(0, width))
        back_color   = np.clip((wall_color.astype(int) * 60 // 100), 0, 255).astype(np.uint8)

        scene = trimesh.Scene()

        # ── 1. FRONT FACE (UV-textured, high-resolution grid) ─────────────
        # Dense enough to show window/door detail from vertex colours if UV fails.
        res_x = min(width,  256)
        res_y = min(height, int(256 * aspect))

        fu  = np.linspace(0.0, 1.0, res_x + 1, dtype=np.float32)
        fv  = np.linspace(0.0, 1.0, res_y + 1, dtype=np.float32)
        fvv, fuu = np.meshgrid(fv, fu, indexing='ij')

        fx = (fuu - 0.5) * face_w
        fy = (0.5 - fvv) * face_h
        fz = np.zeros_like(fx)

        front_verts = np.stack(
            [fx.flatten(), fy.flatten(), fz.flatten()], axis=1
        ).astype(np.float32)
        # UV: v is flipped so image top = OpenGL top
        front_uvs = np.stack(
            [fuu.flatten(), 1.0 - fvv.flatten()], axis=1
        ).astype(np.float32)

        nfx = res_x + 1
        ri  = np.arange(res_y)
        ci  = np.arange(res_x)
        rr, cc = np.meshgrid(ri, ci, indexing='ij')
        v0_idx = (rr * nfx + cc).flatten()
        front_faces = np.concatenate([
            np.stack([v0_idx, v0_idx + 1,       v0_idx + nfx],     axis=1),
            np.stack([v0_idx + 1, v0_idx + nfx + 1, v0_idx + nfx], axis=1),
        ], axis=0).astype(np.int32)

        # High-res vertex colours sampled from the image (used if UV texture fails)
        img_px = np.clip((fuu.flatten() * (width  - 1)).astype(int), 0, width  - 1)
        img_py = np.clip((fvv.flatten() * (height - 1)).astype(int), 0, height - 1)
        front_colors = image[img_py, img_px]

        front_mesh = None
        if image_path is not None:
            try:
                from PIL import Image as PILImage
                pil_img  = PILImage.open(image_path).convert("RGB")
                material = trimesh.visual.material.SimpleMaterial(image=pil_img)
                tex_vis  = trimesh.visual.TextureVisuals(uv=front_uvs, material=material)
                front_mesh = trimesh.Trimesh(
                    vertices=front_verts, faces=front_faces,
                    visual=tex_vis, process=False
                )
                print(f"  🖼️  Front face UV-textured ({res_x}×{res_y} grid, original image)")
            except Exception as tex_err:
                print(f"  ⚠️  UV texture failed ({tex_err}), using hi-res vertex colours")

        if front_mesh is None:
            front_mesh = trimesh.Trimesh(
                vertices=front_verts, faces=front_faces,
                vertex_colors=front_colors, process=False
            )
            print(f"  🎨  Front face vertex-coloured ({res_x}×{res_y} grid)")

        scene.add_geometry(front_mesh, node_name='front_face')

        # ── Helper: coloured quad added directly to the scene ─────────────
        def add_quad(name, p0, p1, p2, p3, color):
            verts  = np.array([p0, p1, p2, p3], dtype=np.float32)
            faces  = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
            colors = np.tile(np.append(color, 255), (4, 1)).astype(np.uint8)
            m = trimesh.Trimesh(vertices=verts, faces=faces,
                                vertex_colors=colors, process=False)
            scene.add_geometry(m, node_name=name)

        # ── 2. LEFT SIDE WALL ─────────────────────────────────────────────
        add_quad('left_wall',
                 [xl, ground_y,  0.0], [xl, roof_y,    0.0],
                 [xl, roof_y,   -building_d], [xl, ground_y, -building_d],
                 left_color)

        # ── 3. RIGHT SIDE WALL ────────────────────────────────────────────
        add_quad('right_wall',
                 [xr, ground_y,  0.0], [xr, ground_y, -building_d],
                 [xr, roof_y,   -building_d], [xr, roof_y,    0.0],
                 right_color)

        # ── 4. ROOF SLAB ──────────────────────────────────────────────────
        add_quad('roof_slab',
                 [xl, roof_y,  0.0], [xr, roof_y,  0.0],
                 [xr, roof_y, -building_d], [xl, roof_y, -building_d],
                 roof_color)

        # ── 5. BACK WALL ──────────────────────────────────────────────────
        add_quad('back_wall',
                 [xl, ground_y, -building_d], [xr, ground_y, -building_d],
                 [xr, roof_y,   -building_d], [xl, roof_y,   -building_d],
                 back_color)

        # ── 6. GROUND PLANE (extends forward in front of building) ────────
        ground_ext = building_d * 0.8
        add_quad('ground_plane',
                 [xl - 0.3, ground_y,  ground_ext],
                 [xr + 0.3, ground_y,  ground_ext],
                 [xr + 0.3, ground_y, -building_d],
                 [xl - 0.3, ground_y, -building_d],
                 ground_color)

        total_faces = sum(len(g.faces) for g in scene.geometry.values())
        print(f"  ✅ Facade Scene: {len(scene.geometry)} meshes, "
              f"{total_faces} total faces | "
              f"roof_y={roof_y:.2f}, ground_y={ground_y:.2f}, depth={building_d:.2f}")
        return scene

    def _architectural_mesh(self, depth_map, image, width, height,
                             scale_factor_x=1.0, scale_factor_z=1.0,
                             complexity="medium", generate_interiors=True):
        """
        Create architectural 3D mesh with proper wall extrusion
        Walls are vertical faces, floors are horizontal planes

        Args:
            depth_map: Binary-like depth (0=floor, 1=wall)
            image: RGB image for colors
            width, height: Dimensions
            complexity: "low" | "medium" | "high" — controls working resolution
                        and contour simplification (more detail = finer walls)
            generate_interiors: when True, build per-room colour-coded floors;
                        when False, a single plain floor slab is used

        Returns:
            mesh: Trimesh object with architectural geometry
        """
        # Complexity → working-resolution cap and contour-simplification factor.
        # Higher complexity keeps more wall detail; lower is faster / coarser.
        complexity = (complexity or "medium").lower()
        res_cap = {"low": 768, "medium": 1024, "high": 1536}.get(complexity, 1024)
        eps_factor = {"low": 0.004, "medium": 0.002, "high": 0.001}.get(complexity, 0.002)

        # Only downsample when the source exceeds the complexity cap. The depth
        # estimator already caps at 1024, so at medium/high this branch usually
        # leaves the wall mask untouched (no thin-wall erosion from re-resizing).
        # Use INTER_NEAREST so the binary wall mask keeps crisp 1px walls instead
        # of INTER_AREA averaging them below the 0.5 threshold and deleting them.
        max_dimension = max(width, height)

        if max_dimension > res_cap:
            target_dim = res_cap
            tw = int(width * target_dim / max_dimension)
            th = int(height * target_dim / max_dimension)
            print(f"  🔽 Downsampling for wall detection: {width}x{height} → {tw}x{th} (INTER_NEAREST)")
            depth_map_small = cv2.resize(depth_map, (tw, th), interpolation=cv2.INTER_NEAREST)
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

        # Architectural parameters — Y-up, floor plan in XZ plane, walls extrude +Y
        # When a real-world scale is applied (scale_factor != 1), ceiling is 3.0m.
        # In normalized mode (scale_factor = 1.0), keep legacy 2.5 unit height.
        has_real_scale = (scale_factor_x != 1.0 or scale_factor_z != 1.0)
        ceiling_height = 3.0 if has_real_scale else 2.5
        floor_height = 0.0
        wall_thickness = 0.08 * max(scale_factor_x, scale_factor_z) if has_real_scale else 0.08
        print(f"  📐 Y-up: Floor=XZ (Y={floor_height}), Ceiling Y={ceiling_height:.2f}, "
              f"scale=({scale_factor_x:.2f}, {scale_factor_z:.2f})")

        # Map pixel coordinates to 3D world space.
        if has_real_scale:
            # Real-world metres: scale_factor_{x,z} already encode the drawing's
            # true width/height (derived from the source pixel aspect in app.py),
            # so independent x/z scaling here is correct and aspect-faithful.
            scale_x = 2.0 / w_small * scale_factor_x
            scale_z = 2.0 / h_small * scale_factor_z
            offset_x = -1.0 * scale_factor_x
            offset_z = -1.0 * scale_factor_z
            half_x = scale_factor_x
            half_z = scale_factor_z
        else:
            # Normalized mode: use ONE uniform scale so the plan's real aspect
            # ratio is preserved. Previously x used 2/w and z used 2/h
            # independently, which squashed every plan into a 2x2 square (a wide
            # plan came out square). Longest side now spans 2 units, centred.
            uniform = 2.0 / max(w_small, h_small)
            scale_x = scale_z = uniform
            half_x = w_small * uniform / 2.0
            half_z = h_small * uniform / 2.0
            offset_x = -half_x
            offset_z = -half_z

        vertices = []
        faces = []
        colors = []
        wall_vertex_count = 0
        vertex_offset = 0

        def _add_wall_quad(xa, za, xb, zb, y_bot, y_top, color):
            nonlocal vertex_offset
            if y_top <= y_bot:
                return
            seg_dx = xb - xa;  seg_dz = zb - za
            seg_len = max(np.sqrt(seg_dx**2 + seg_dz**2), 1e-6)
            # Perpendicular offset for wall thickness (inner face)
            nx = seg_dz / seg_len * wall_thickness
            nz = -seg_dx / seg_len * wall_thickness
            inner_c = [min(255, int(c) + 15) for c in color]
            top_c   = [min(255, int(c) + 30) for c in color]

            # Outer face
            vertices.extend([[xa, y_bot, za], [xb, y_bot, zb], [xb, y_top, zb], [xa, y_top, za]])
            colors.extend([color] * 4)
            b = vertex_offset
            faces.extend([[b, b+1, b+2], [b, b+2, b+3]])
            vertex_offset += 4

            # Inner face (reversed winding so normal faces inward)
            vertices.extend([[xa+nx, y_bot, za+nz], [xb+nx, y_bot, zb+nz],
                              [xb+nx, y_top, zb+nz], [xa+nx, y_top, za+nz]])
            colors.extend([inner_c] * 4)
            b = vertex_offset
            faces.extend([[b+2, b+1, b], [b+3, b+2, b]])
            vertex_offset += 4

            # Top cap (only at full ceiling height to avoid floating caps on lintels)
            if abs(y_top - ceiling_height) < 0.05:
                vertices.extend([[xa, y_top, za], [xb, y_top, zb],
                                  [xb+nx, y_top, zb+nz], [xa+nx, y_top, za+nz]])
                colors.extend([top_c] * 4)
                b = vertex_offset
                faces.extend([[b, b+1, b+2], [b, b+2, b+3]])
                vertex_offset += 4

        min_contour_perimeter = min(w_small, h_small) * 0.04

        for contour_idx, contour in enumerate(contours):
            if len(contour) < 4:
                continue

            perimeter = cv2.arcLength(contour, True)
            if perimeter < min_contour_perimeter:
                continue

            epsilon = eps_factor * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if len(approx) < 3:
                continue

            # Sample wall color from floor plan image at contour location
            # Use median color along the contour for realistic appearance
            contour_colors = []
            for point in approx:
                px, py = point[0]
                if 0 <= py < h_small and 0 <= px < w_small:
                    contour_colors.append(image_small[py, px])
            wall_color = (np.median(contour_colors, axis=0).astype(np.uint8).tolist()
                          if contour_colors else [120, 120, 120])

            door_top = min(2.1 * (ceiling_height / 3.0), ceiling_height - 0.1)

            seg_count = len(approx)
            for i in range(seg_count):
                p1 = approx[i][0]
                p2 = approx[(i + 1) % seg_count][0]

                x1 = p1[0] * scale_x + offset_x
                z1 = -(p1[1] * scale_z + offset_z)
                x2 = p2[0] * scale_x + offset_x
                z2 = -(p2[1] * scale_z + offset_z)

                openings = self._detect_segment_openings(
                    image_small, p1[0], p1[1], p2[0], p2[1], h_small, w_small
                )

                if not openings:
                    _add_wall_quad(x1, z1, x2, z2, floor_height, ceiling_height, wall_color)
                else:
                    prev_t = 0.0
                    for gap_s, gap_e in openings:
                        # Solid wall section before this opening
                        if gap_s > prev_t + 0.02:
                            xa = x1 + (x2 - x1) * prev_t;  za = z1 + (z2 - z1) * prev_t
                            xb = x1 + (x2 - x1) * gap_s;   zb = z1 + (z2 - z1) * gap_s
                            _add_wall_quad(xa, za, xb, zb, floor_height, ceiling_height, wall_color)
                        # Lintel only over the opening (door height to ceiling)
                        xc = x1 + (x2 - x1) * gap_s;  zc = z1 + (z2 - z1) * gap_s
                        xd = x1 + (x2 - x1) * gap_e;  zd = z1 + (z2 - z1) * gap_e
                        lintel_c = [min(255, int(c) + 25) for c in wall_color]
                        _add_wall_quad(xc, zc, xd, zd, door_top, ceiling_height, lintel_c)
                        prev_t = gap_e
                    # Solid wall section after last opening
                    if prev_t < 0.98:
                        xa = x1 + (x2 - x1) * prev_t;  za = z1 + (z2 - z1) * prev_t
                        _add_wall_quad(xa, za, x2, z2, floor_height, ceiling_height, wall_color)

        wall_vertex_count = vertex_offset  # all verts so far are wall geometry

        # Fallback: no usable wall geometry extracted from this depth map
        if wall_vertex_count == 0:
            print("  ⚠️  No wall geometry from contours — retrying with lower threshold")
            wall_mask_retry = (depth_map_small > 0.3).astype(np.uint8) * 255
            contours_retry, _ = cv2.findContours(
                wall_mask_retry, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
            )
            if contours_retry:
                depth_retry = wall_mask_retry.astype(np.float32) / 255.0
                img_retry = image_small if max_dimension > res_cap else image
                return self._architectural_mesh(depth_retry, img_retry, w_small, h_small,
                                               scale_factor_x, scale_factor_z,
                                               complexity, generate_interiors)
            print("  ⚠️  Still no walls — falling back to depth heightmap")
            return self._depth_to_mesh(depth_map, image, width, height, image_path=None)

        # Room-colored floors — one color per detected room (interior detail).
        # Skipped when the user turns off interior elements; a plain slab is used.
        room_data = None
        if generate_interiors:
            room_data = self._build_room_floors(
                depth_map_small, h_small, w_small,
                scale_x, scale_z, offset_x, offset_z, floor_height
            )
        if room_data is not None:
            rv, rf, rc = room_data
            rf_shifted = rf + vertex_offset
            vertices.extend(rv.tolist())
            faces.extend(rf_shifted.tolist())
            colors.extend(rc.tolist())
            vertex_offset += len(rv)
        else:
            # Single warm-beige floor slab spanning the (aspect-correct) footprint
            vertices.extend([[-half_x, floor_height, -half_z], [ half_x, floor_height, -half_z],
                              [ half_x, floor_height,  half_z], [-half_x, floor_height,  half_z]])
            colors.extend([[230, 215, 190]] * 4)
            b = vertex_offset
            faces.extend([[b, b+1, b+2], [b, b+2, b+3]])
            vertex_offset += 4

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

    def _detect_segment_openings(self, image, px1, py1, px2, py2, h, w):
        """
        Sample image brightness along a wall contour segment to find door/window
        openings (bright white gaps in the dark wall lines).
        Returns list of (t_start, t_end) positions, normalized to [0, 1].
        """
        dx = px2 - px1
        dy = py2 - py1
        seg_len = max(np.sqrt(dx * dx + dy * dy), 1.0)
        n_samples = max(int(seg_len), 6)

        samples = []
        for i in range(n_samples):
            t = i / max(n_samples - 1, 1)
            ix = int(np.clip(px1 + t * dx, 0, w - 1))
            iy = int(np.clip(py1 + t * dy, 0, h - 1))
            samples.append((t, float(np.mean(image[iy, ix])) > 195))

        gaps = []
        in_gap = False
        gap_start = 0.0
        for t, is_bright in samples:
            if is_bright and not in_gap:
                in_gap = True
                gap_start = t
            elif not is_bright and in_gap:
                in_gap = False
                if t - gap_start > 0.07:
                    gaps.append((gap_start, t))
        if in_gap and 1.0 - gap_start > 0.07:
            gaps.append((gap_start, 1.0))
        return gaps

    def _build_room_floors(self, depth_map, h, w,
                            scale_x, scale_z, offset_x, offset_z, floor_height):
        """
        Flood-fill floor areas between walls to detect individual rooms, then build
        a color-coded floor mesh — one distinct warm color per room.
        Returns (vertices, faces, colors) arrays, or None if no rooms found.
        """
        wall_mask  = (depth_map > 0.5).astype(np.uint8) * 255
        floor_mask = cv2.bitwise_not(wall_mask)

        # Erode so narrow doorways don't merge adjacent rooms in the component pass
        kernel = np.ones((5, 5), np.uint8)
        floor_eroded = cv2.erode(floor_mask, kernel, iterations=2)

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            floor_eroded, connectivity=4
        )

        total_area = h * w
        # Architect-friendly palette: warm, distinct, low-saturation tones
        PALETTE = [
            [232, 218, 200],  # tan — unlabelled background floor
            [248, 238, 220],  # cream — living / main room
            [218, 232, 246],  # sky blue — bedroom
            [228, 244, 222],  # sage — kitchen / dining
            [246, 232, 220],  # peach — bedroom 2
            [234, 220, 246],  # lavender — study / office
            [220, 244, 238],  # mint — bathroom
            [244, 240, 218],  # pale gold — utility / laundry
        ]

        # Sort rooms largest → smallest so the main room gets the "cream" color
        room_list = sorted(
            [(idx, stats[idx, cv2.CC_STAT_AREA])
             for idx in range(1, num_labels)
             if stats[idx, cv2.CC_STAT_AREA] >= total_area * 0.003],
            key=lambda x: -x[1]
        )
        label_color = {lbl: PALETTE[min(rank + 1, len(PALETTE) - 1)]
                       for rank, (lbl, _) in enumerate(room_list)}

        if not room_list:
            return None

        print(f"  🏘️  Room detection: {len(room_list)} rooms found")

        step = max(3, min(w, h) // 64)
        verts, face_list, col_list = [], [], []
        v_off = 0

        for py in range(0, h - step, step):
            for px in range(0, w - step, step):
                cy, cx = py + step // 2, px + step // 2
                if cy >= h or cx >= w:
                    continue
                if floor_mask[cy, cx] == 0:
                    continue  # skip wall area
                lbl = int(labels[cy, cx]) if cy < labels.shape[0] and cx < labels.shape[1] else 0
                color = label_color.get(lbl, PALETTE[0])

                x0 = px * scale_x + offset_x
                x1 = min(px + step, w) * scale_x + offset_x
                z0 = -(py * scale_z + offset_z)
                z1 = -(min(py + step, h) * scale_z + offset_z)

                verts.extend([[x0, floor_height, z0], [x1, floor_height, z0],
                               [x1, floor_height, z1], [x0, floor_height, z1]])
                col_list.extend([color] * 4)
                b = v_off
                face_list.extend([[b, b+1, b+2], [b, b+2, b+3]])
                v_off += 4

        if not verts:
            return None

        return (np.array(verts,      dtype=np.float32),
                np.array(face_list,  dtype=np.int32),
                np.array(col_list,   dtype=np.uint8))

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
