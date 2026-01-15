"""
Procedural Generation Module
Generates/hallucinates unseen areas like room interiors, behind walls, etc.
Uses trimesh instead of Open3D for better server compatibility
"""

import numpy as np
import trimesh
from scipy.spatial import Delaunay
import cv2


class ProceduralGenerator:
    """Procedurally generates unseen geometry to create complete 3D environments"""

    def __init__(self):
        print("🔧 Initializing Procedural Generator (trimesh-based)")
        self.wall_thickness = 0.3
        self.floor_height = 0.1
        self.ceiling_height = 3.0

    def generate_unseen_geometry(self, base_mesh, image_data, depth_map, options):
        """
        Main method to generate unseen areas

        Args:
            base_mesh: The base trimesh from depth estimation
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
            vertices = base_mesh.vertices
            bounds = self._get_bounds(vertices)

            # Generate based on scene type and complexity
            procedural_meshes = [base_mesh]

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
            enhanced_mesh = trimesh.util.concatenate(procedural_meshes)

            # Trimesh concatenate automatically cleans and validates the mesh
            print(f"✅ Enhanced mesh: {len(enhanced_mesh.vertices)} vertices, {len(enhanced_mesh.faces)} faces")

            return enhanced_mesh

        except Exception as e:
            print(f"⚠️  Error in procedural generation: {e}")
            print("  Returning base mesh without enhancements")
            return base_mesh

    def _detect_scene_type(self, image_data, depth_map):
        """Detect the type of scene"""
        avg_color = np.mean(image_data, axis=(0, 1))
        depth_variance = np.var(depth_map)
        avg_depth = np.mean(depth_map)

        if depth_variance < 0.02:
            return 'flat_wall'
        elif avg_color[2] > 150 and avg_color[0] < 100:
            return 'exterior'
        elif avg_depth > 0.7:
            return 'landscape'
        elif np.var(image_data) < 500:
            return 'interior'
        else:
            return 'building'

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
            depth_offset = bounds['size'][2] * 0.3
            min_x, min_y = bounds['min'][0], bounds['min'][1]
            max_x, max_y = bounds['max'][0], bounds['max'][1]
            back_z = bounds['min'][2] - depth_offset

            wall_vertices = np.array([
                [min_x, min_y, back_z],
                [max_x, min_y, back_z],
                [max_x, max_y, back_z],
                [min_x, max_y, back_z],
                [min_x, min_y, back_z - self.wall_thickness],
                [max_x, min_y, back_z - self.wall_thickness],
                [max_x, max_y, back_z - self.wall_thickness],
                [min_x, max_y, back_z - self.wall_thickness],
            ])

            wall_faces = np.array([
                [0, 1, 2], [0, 2, 3],
                [4, 6, 5], [4, 7, 6],
                [0, 4, 5], [0, 5, 1],
                [1, 5, 6], [1, 6, 2],
                [2, 6, 7], [2, 7, 3],
                [3, 7, 4], [3, 4, 0],
            ])

            wall_mesh = trimesh.Trimesh(vertices=wall_vertices, faces=wall_faces)
            wall_mesh.visual.vertex_colors = [180, 180, 180, 255]
            return wall_mesh

        except Exception as e:
            print(f"  ⚠️  Could not generate back walls: {e}")
            return None

    def _generate_floor(self, bounds, vertices):
        """Generate floor plane"""
        try:
            floor_y = bounds['min'][1] - 0.05
            min_x, max_x = bounds['min'][0], bounds['max'][0]
            min_z, max_z = bounds['min'][2], bounds['max'][2]

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
                [min_x, floor_y - self.floor_height, min_z],
                [max_x, floor_y - self.floor_height, min_z],
                [max_x, floor_y - self.floor_height, max_z],
                [min_x, floor_y - self.floor_height, max_z],
            ])

            floor_faces = np.array([
                [0, 2, 1], [0, 3, 2],
                [4, 5, 6], [4, 6, 7],
                [0, 1, 5], [0, 5, 4],
                [1, 2, 6], [1, 6, 5],
                [2, 3, 7], [2, 7, 6],
                [3, 0, 4], [3, 4, 7],
            ])

            floor_mesh = trimesh.Trimesh(vertices=floor_vertices, faces=floor_faces)
            floor_mesh.visual.vertex_colors = [75, 75, 75, 255]
            return floor_mesh

        except Exception as e:
            print(f"  ⚠️  Could not generate floor: {e}")
            return None

    def _generate_side_walls(self, bounds, vertices):
        """Generate left and right walls"""
        walls = []

        try:
            left_x = bounds['min'][0] - self.wall_thickness
            right_x = bounds['max'][0] + self.wall_thickness
            min_y, max_y = bounds['min'][1], bounds['max'][1]
            min_z, max_z = bounds['min'][2], bounds['max'][2]

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
                    [x_pos + self.wall_thickness if is_left else x_pos - self.wall_thickness, min_y, min_z],
                    [x_pos + self.wall_thickness if is_left else x_pos - self.wall_thickness, min_y, max_z],
                    [x_pos + self.wall_thickness if is_left else x_pos - self.wall_thickness, max_y, max_z],
                    [x_pos + self.wall_thickness if is_left else x_pos - self.wall_thickness, max_y, min_z],
                ])

                wall_faces = np.array([
                    [0, 1, 2], [0, 2, 3],
                    [4, 6, 5], [4, 7, 6],
                    [0, 4, 5], [0, 5, 1],
                    [1, 5, 6], [1, 6, 2],
                    [2, 6, 7], [2, 7, 3],
                    [3, 7, 4], [3, 4, 0],
                ])

                wall_mesh = trimesh.Trimesh(vertices=wall_vertices, faces=wall_faces)
                wall_mesh.visual.vertex_colors = [165, 165, 165, 255]
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
                [min_x, ceiling_y + self.floor_height, min_z],
                [max_x, ceiling_y + self.floor_height, min_z],
                [max_x, ceiling_y + self.floor_height, max_z],
                [min_x, ceiling_y + self.floor_height, max_z],
            ])

            ceiling_faces = np.array([
                [0, 1, 2], [0, 2, 3],
                [4, 6, 5], [4, 7, 6],
                [0, 5, 1], [0, 4, 5],
                [1, 6, 2], [1, 5, 6],
                [2, 7, 3], [2, 6, 7],
                [3, 4, 0], [3, 7, 4],
            ])

            ceiling_mesh = trimesh.Trimesh(vertices=ceiling_vertices, faces=ceiling_faces)
            ceiling_mesh.visual.vertex_colors = [200, 200, 200, 255]
            return ceiling_mesh

        except Exception as e:
            print(f"  ⚠️  Could not generate ceiling: {e}")
            return None

    def _generate_interior_elements(self, scene_type, bounds, complexity):
        """Generate interior elements based on scene type"""
        elements = []

        try:
            if scene_type == 'factory':
                elements.extend(self._generate_industrial_elements(bounds, complexity))
            elif scene_type == 'interior':
                elements.extend(self._generate_room_elements(bounds, complexity))
            elif scene_type == 'building':
                elements.extend(self._generate_structural_elements(bounds, complexity))
        except Exception as e:
            print(f"  ⚠️  Could not generate interior elements: {e}")

        return elements

    def _generate_industrial_elements(self, bounds, complexity):
        """Generate factory/industrial elements"""
        elements = []

        try:
            catwalk_y = bounds['min'][1] + bounds['size'][1] * 0.5
            catwalk_z = bounds['center'][2]
            catwalk_width = 1.0
            catwalk_length = bounds['size'][0] * 0.8

            catwalk = trimesh.creation.box(
                extents=[catwalk_length, 0.1, catwalk_width]
            )
            catwalk.apply_translation([
                bounds['min'][0] + bounds['size'][0] * 0.1 + catwalk_length/2,
                catwalk_y,
                catwalk_z
            ])
            catwalk.visual.vertex_colors = [100, 100, 100, 255]
            elements.append(catwalk)

            if complexity == 'high':
                pipe = trimesh.creation.cylinder(radius=0.1, height=bounds['size'][2])
                rotation_matrix = trimesh.transformations.rotation_matrix(
                    np.pi/2, [0, 1, 0]
                )
                pipe.apply_transform(rotation_matrix)
                pipe.apply_translation([bounds['center'][0], bounds['max'][1] - 0.5, bounds['center'][2]])
                pipe.visual.vertex_colors = [130, 130, 130, 255]
                elements.append(pipe)

        except Exception as e:
            print(f"  ⚠️  Error generating industrial elements: {e}")

        return elements

    def _generate_room_elements(self, bounds, complexity):
        """Generate room elements"""
        elements = []

        if complexity in ['medium', 'high']:
            try:
                box_size = bounds['size'][0] * 0.15
                box = trimesh.creation.box(
                    extents=[box_size, box_size * 0.8, box_size]
                )
                box.apply_translation([
                    bounds['center'][0],
                    bounds['min'][1] + box_size * 0.4,
                    bounds['min'][2] + bounds['size'][2] * 0.3
                ])
                box.visual.vertex_colors = [150, 100, 75, 255]
                elements.append(box)

            except Exception as e:
                print(f"  ⚠️  Error generating room elements: {e}")

        return elements

    def _generate_structural_elements(self, bounds, complexity):
        """Generate structural elements like pillars"""
        elements = []

        if complexity == 'high':
            try:
                pillar_radius = 0.2
                pillar_height = bounds['size'][1]

                positions = [
                    [bounds['min'][0], bounds['min'][1], bounds['min'][2]],
                    [bounds['max'][0], bounds['min'][1], bounds['min'][2]],
                ]

                for pos in positions:
                    pillar = trimesh.creation.cylinder(
                        radius=pillar_radius,
                        height=pillar_height
                    )
                    pillar.apply_translation([pos[0], pos[1] + pillar_height / 2, pos[2]])
                    pillar.visual.vertex_colors = [130, 130, 130, 255]
                    elements.append(pillar)

            except Exception as e:
                print(f"  ⚠️  Error generating structural elements: {e}")

        return elements
