"""
Procedural Generation Module
Generates/hallucinates unseen areas like room interiors, behind walls, etc.
"""

import numpy as np
import open3d as o3d
from scipy.spatial import Delaunay
import cv2


class ProceduralGenerator:
    """Procedurally generates unseen geometry to create complete 3D environments"""

    def __init__(self):
        print("🔧 Initializing Procedural Generator")
        self.wall_thickness = 0.3
        self.floor_height = 0.1
        self.ceiling_height = 3.0

    def generate_unseen_geometry(self, base_mesh, image_data, depth_map, options):
        """
        Main method to generate unseen areas

        Args:
            base_mesh: The base mesh from depth estimation
            image_data: Original image
            depth_map: Depth values
            options: Generation options (wall_thickness, complexity, etc.)

        Returns:
            enhanced_mesh: Mesh with added procedural geometry
        """
        print("🎨 Generating unseen geometry...")

        try:
            # Extract options
            complexity = options.get('room_complexity', 'medium')
            self.wall_thickness = options.get('wall_thickness', 0.3)
            generate_interiors = options.get('generate_interiors', True)

            # Analyze the scene
            scene_type = self._detect_scene_type(image_data, depth_map)
            print(f"  Detected scene type: {scene_type}")

            # Get mesh bounds
            vertices = np.asarray(base_mesh.vertices)
            bounds = self._get_bounds(vertices)

            # Generate based on scene type and complexity
            procedural_meshes = []

            # 1. Generate back walls (assuming front view)
            if generate_interiors:
                back_walls = self._generate_back_walls(bounds, vertices, depth_map)
                if back_walls:
                    procedural_meshes.append(back_walls)

            # 2. Generate floor
            floor_mesh = self._generate_floor(bounds, vertices)
            if floor_mesh:
                procedural_meshes.append(floor_mesh)

            # 3. Generate side walls
            if generate_interiors:
                side_walls = self._generate_side_walls(bounds, vertices)
                if side_walls:
                    procedural_meshes.extend(side_walls)

            # 4. Generate interior elements based on scene type
            if generate_interiors and complexity in ['medium', 'high']:
                interior_elements = self._generate_interior_elements(
                    scene_type,
                    bounds,
                    complexity
                )
                procedural_meshes.extend(interior_elements)

            # 5. Add ceiling if interior scene
            if generate_interiors and scene_type in ['interior', 'factory', 'building']:
                ceiling = self._generate_ceiling(bounds)
                if ceiling:
                    procedural_meshes.append(ceiling)

            # Combine all meshes
            enhanced_mesh = base_mesh
            for proc_mesh in procedural_meshes:
                enhanced_mesh += proc_mesh

            # Clean up combined mesh
            enhanced_mesh.remove_duplicated_vertices()
            enhanced_mesh.remove_duplicated_triangles()
            enhanced_mesh.compute_vertex_normals()

            print(f"✅ Enhanced mesh: {len(enhanced_mesh.vertices)} vertices, {len(enhanced_mesh.triangles)} triangles")

            return enhanced_mesh

        except Exception as e:
            print(f"⚠️  Error in procedural generation: {e}")
            print("  Returning base mesh without enhancements")
            return base_mesh

    def _detect_scene_type(self, image_data, depth_map):
        """
        Detect the type of scene (interior, exterior, factory, etc.)

        Args:
            image_data: RGB image
            depth_map: Depth values

        Returns:
            scene_type: String indicating scene type
        """
        # Simple heuristic-based detection
        # In production, could use a classifier

        # Calculate color statistics
        avg_color = np.mean(image_data, axis=(0, 1))
        color_variance = np.var(image_data, axis=(0, 1))

        # Calculate depth statistics
        depth_variance = np.var(depth_map)
        avg_depth = np.mean(depth_map)

        # Simple rules (can be improved)
        if depth_variance < 0.02:  # Low depth variation
            return 'flat_wall'
        elif avg_color[2] > 150 and avg_color[0] < 100:  # Bluish (sky)
            return 'exterior'
        elif avg_depth > 0.7:  # Far away average
            return 'landscape'
        elif color_variance.mean() < 500:  # Low color variation
            return 'interior'
        else:
            return 'building'  # Default

    def _get_bounds(self, vertices):
        """Get bounding box of vertices"""
        min_bounds = np.min(vertices, axis=0)
        max_bounds = np.max(vertices, axis=0)
        center = (min_bounds + max_bounds) / 2
        size = max_bounds - min_bounds

        return {
            'min': min_bounds,
            'max': max_bounds,
            'center': center,
            'size': size
        }

    def _generate_back_walls(self, bounds, vertices, depth_map):
        """Generate back walls behind the visible surface"""
        try:
            # Create a wall at the back depth
            depth_offset = bounds['size'][2] * 0.3  # 30% behind the furthest point

            min_x, min_y = bounds['min'][0], bounds['min'][1]
            max_x, max_y = bounds['max'][0], bounds['max'][1]
            back_z = bounds['min'][2] - depth_offset

            # Create wall vertices
            wall_vertices = np.array([
                [min_x, min_y, back_z],
                [max_x, min_y, back_z],
                [max_x, max_y, back_z],
                [min_x, max_y, back_z],
                # Add thickness
                [min_x, min_y, back_z - self.wall_thickness],
                [max_x, min_y, back_z - self.wall_thickness],
                [max_x, max_y, back_z - self.wall_thickness],
                [min_x, max_y, back_z - self.wall_thickness],
            ])

            # Create triangles for the wall
            wall_triangles = np.array([
                # Front face
                [0, 1, 2], [0, 2, 3],
                # Back face
                [4, 6, 5], [4, 7, 6],
                # Sides
                [0, 4, 5], [0, 5, 1],
                [1, 5, 6], [1, 6, 2],
                [2, 6, 7], [2, 7, 3],
                [3, 7, 4], [3, 4, 0],
            ])

            # Create mesh
            wall_mesh = o3d.geometry.TriangleMesh()
            wall_mesh.vertices = o3d.utility.Vector3dVector(wall_vertices)
            wall_mesh.triangles = o3d.utility.Vector3iVector(wall_triangles)

            # Add color (grayish)
            wall_color = [0.7, 0.7, 0.7]
            wall_mesh.paint_uniform_color(wall_color)

            wall_mesh.compute_vertex_normals()

            return wall_mesh

        except Exception as e:
            print(f"  ⚠️  Could not generate back walls: {e}")
            return None

    def _generate_floor(self, bounds, vertices):
        """Generate floor plane"""
        try:
            # Floor at bottom Y
            floor_y = bounds['min'][1] - 0.05

            min_x, max_x = bounds['min'][0], bounds['max'][0]
            min_z, max_z = bounds['min'][2], bounds['max'][2]

            # Extend floor beyond bounds
            margin = max(bounds['size'][0], bounds['size'][2]) * 0.2
            min_x -= margin
            max_x += margin
            min_z -= margin
            max_z += margin

            floor_vertices = np.array([
                [min_x, floor_y, min_z],
                [max_x, floor_y, min_z],
                [max_x, floor_y, max_z],
                [min_x, floor_y, max_z],
                # Bottom
                [min_x, floor_y - self.floor_height, min_z],
                [max_x, floor_y - self.floor_height, min_z],
                [max_x, floor_y - self.floor_height, max_z],
                [min_x, floor_y - self.floor_height, max_z],
            ])

            floor_triangles = np.array([
                [0, 2, 1], [0, 3, 2],  # Top
                [4, 5, 6], [4, 6, 7],  # Bottom
                # Sides
                [0, 1, 5], [0, 5, 4],
                [1, 2, 6], [1, 6, 5],
                [2, 3, 7], [2, 7, 6],
                [3, 0, 4], [3, 4, 7],
            ])

            floor_mesh = o3d.geometry.TriangleMesh()
            floor_mesh.vertices = o3d.utility.Vector3dVector(floor_vertices)
            floor_mesh.triangles = o3d.utility.Vector3iVector(floor_triangles)

            # Dark gray floor
            floor_mesh.paint_uniform_color([0.3, 0.3, 0.3])
            floor_mesh.compute_vertex_normals()

            return floor_mesh

        except Exception as e:
            print(f"  ⚠️  Could not generate floor: {e}")
            return None

    def _generate_side_walls(self, bounds, vertices):
        """Generate left and right walls"""
        walls = []

        try:
            # Left wall
            left_x = bounds['min'][0] - self.wall_thickness
            right_x = bounds['max'][0] + self.wall_thickness

            min_y, max_y = bounds['min'][1], bounds['max'][1]
            min_z, max_z = bounds['min'][2], bounds['max'][2]

            # Extend walls
            margin_y = bounds['size'][1] * 0.1
            margin_z = bounds['size'][2] * 0.2

            min_y -= margin_y
            max_y += margin_y
            min_z -= margin_z

            for x_pos, is_left in [(left_x, True), (right_x, False)]:
                wall_vertices = np.array([
                    [x_pos, min_y, min_z],
                    [x_pos, min_y, max_z],
                    [x_pos, max_y, max_z],
                    [x_pos, max_y, min_z],
                    # Back side
                    [x_pos + self.wall_thickness if is_left else x_pos - self.wall_thickness, min_y, min_z],
                    [x_pos + self.wall_thickness if is_left else x_pos - self.wall_thickness, min_y, max_z],
                    [x_pos + self.wall_thickness if is_left else x_pos - self.wall_thickness, max_y, max_z],
                    [x_pos + self.wall_thickness if is_left else x_pos - self.wall_thickness, max_y, min_z],
                ])

                wall_triangles = np.array([
                    [0, 1, 2], [0, 2, 3],  # Front
                    [4, 6, 5], [4, 7, 6],  # Back
                    # Connect sides
                    [0, 4, 5], [0, 5, 1],
                    [1, 5, 6], [1, 6, 2],
                    [2, 6, 7], [2, 7, 3],
                    [3, 7, 4], [3, 4, 0],
                ])

                wall_mesh = o3d.geometry.TriangleMesh()
                wall_mesh.vertices = o3d.utility.Vector3dVector(wall_vertices)
                wall_mesh.triangles = o3d.utility.Vector3iVector(wall_triangles)
                wall_mesh.paint_uniform_color([0.65, 0.65, 0.65])
                wall_mesh.compute_vertex_normals()

                walls.append(wall_mesh)

            return walls

        except Exception as e:
            print(f"  ⚠️  Could not generate side walls: {e}")
            return []

    def _generate_ceiling(self, bounds):
        """Generate ceiling"""
        try:
            ceiling_y = bounds['max'][1] + self.ceiling_height

            min_x, max_x = bounds['min'][0], bounds['max'][0]
            min_z, max_z = bounds['min'][2], bounds['max'][2]

            # Extend ceiling
            margin = max(bounds['size'][0], bounds['size'][2]) * 0.2
            min_x -= margin
            max_x += margin
            min_z -= margin
            max_z += margin

            ceiling_vertices = np.array([
                [min_x, ceiling_y, min_z],
                [max_x, ceiling_y, min_z],
                [max_x, ceiling_y, max_z],
                [min_x, ceiling_y, max_z],
                # Top
                [min_x, ceiling_y + self.floor_height, min_z],
                [max_x, ceiling_y + self.floor_height, min_z],
                [max_x, ceiling_y + self.floor_height, max_z],
                [min_x, ceiling_y + self.floor_height, max_z],
            ])

            ceiling_triangles = np.array([
                [0, 1, 2], [0, 2, 3],  # Bottom
                [4, 6, 5], [4, 7, 6],  # Top
                [0, 5, 1], [0, 4, 5],
                [1, 6, 2], [1, 5, 6],
                [2, 7, 3], [2, 6, 7],
                [3, 4, 0], [3, 7, 4],
            ])

            ceiling_mesh = o3d.geometry.TriangleMesh()
            ceiling_mesh.vertices = o3d.utility.Vector3dVector(ceiling_vertices)
            ceiling_mesh.triangles = o3d.utility.Vector3iVector(ceiling_triangles)
            ceiling_mesh.paint_uniform_color([0.8, 0.8, 0.8])
            ceiling_mesh.compute_vertex_normals()

            return ceiling_mesh

        except Exception as e:
            print(f"  ⚠️  Could not generate ceiling: {e}")
            return None

    def _generate_interior_elements(self, scene_type, bounds, complexity):
        """
        Generate interior elements based on scene type

        Args:
            scene_type: Type of scene detected
            bounds: Bounding box of scene
            complexity: 'low', 'medium', or 'high'

        Returns:
            List of mesh objects
        """
        elements = []

        try:
            if scene_type == 'factory':
                # Add industrial elements
                elements.extend(self._generate_industrial_elements(bounds, complexity))
            elif scene_type == 'interior':
                # Add room elements
                elements.extend(self._generate_room_elements(bounds, complexity))
            elif scene_type == 'building':
                # Add structural elements
                elements.extend(self._generate_structural_elements(bounds, complexity))

        except Exception as e:
            print(f"  ⚠️  Could not generate interior elements: {e}")

        return elements

    def _generate_industrial_elements(self, bounds, complexity):
        """Generate factory/industrial elements like catwalks, machinery"""
        elements = []

        try:
            # Add a simple catwalk
            catwalk_y = bounds['min'][1] + bounds['size'][1] * 0.5
            catwalk_z = bounds['center'][2]

            catwalk_width = 1.0
            catwalk_length = bounds['size'][0] * 0.8

            catwalk = o3d.geometry.TriangleMesh.create_box(
                width=catwalk_length,
                height=0.1,
                depth=catwalk_width
            )

            catwalk.translate([
                bounds['min'][0] + bounds['size'][0] * 0.1,
                catwalk_y,
                catwalk_z - catwalk_width / 2
            ])

            catwalk.paint_uniform_color([0.4, 0.4, 0.4])
            catwalk.compute_vertex_normals()
            elements.append(catwalk)

            if complexity == 'high':
                # Add some pipes
                pipe = o3d.geometry.TriangleMesh.create_cylinder(radius=0.1, height=bounds['size'][2])
                pipe.rotate(
                    pipe.get_rotation_matrix_from_xyz((0, np.pi/2, 0)),
                    center=(0, 0, 0)
                )
                pipe.translate([bounds['center'][0], bounds['max'][1] - 0.5, bounds['center'][2]])
                pipe.paint_uniform_color([0.5, 0.5, 0.5])
                pipe.compute_vertex_normals()
                elements.append(pipe)

        except Exception as e:
            print(f"  ⚠️  Error generating industrial elements: {e}")

        return elements

    def _generate_room_elements(self, bounds, complexity):
        """Generate room elements"""
        elements = []

        # Add a simple box as furniture placeholder
        if complexity in ['medium', 'high']:
            try:
                box_size = bounds['size'][0] * 0.15

                box = o3d.geometry.TriangleMesh.create_box(
                    width=box_size,
                    height=box_size * 0.8,
                    depth=box_size
                )

                box.translate([
                    bounds['center'][0] - box_size / 2,
                    bounds['min'][1],
                    bounds['min'][2] + bounds['size'][2] * 0.3
                ])

                box.paint_uniform_color([0.6, 0.4, 0.3])
                box.compute_vertex_normals()
                elements.append(box)

            except Exception as e:
                print(f"  ⚠️  Error generating room elements: {e}")

        return elements

    def _generate_structural_elements(self, bounds, complexity):
        """Generate structural elements like pillars"""
        elements = []

        if complexity == 'high':
            try:
                # Add corner pillars
                pillar_radius = 0.2
                pillar_height = bounds['size'][1]

                positions = [
                    [bounds['min'][0], bounds['min'][1], bounds['min'][2]],
                    [bounds['max'][0], bounds['min'][1], bounds['min'][2]],
                ]

                for pos in positions:
                    pillar = o3d.geometry.TriangleMesh.create_cylinder(
                        radius=pillar_radius,
                        height=pillar_height
                    )
                    pillar.translate([pos[0], pos[1] + pillar_height / 2, pos[2]])
                    pillar.paint_uniform_color([0.5, 0.5, 0.5])
                    pillar.compute_vertex_normals()
                    elements.append(pillar)

            except Exception as e:
                print(f"  ⚠️  Error generating structural elements: {e}")

        return elements
