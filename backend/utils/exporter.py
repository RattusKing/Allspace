"""
Model Exporter Module
Exports 3D meshes to various formats (GLB, FBX, OBJ)
"""

import os
import numpy as np
import open3d as o3d
import trimesh
from PIL import Image


class ModelExporter:
    """Exports 3D models to various formats compatible with Unity, Unreal, Blender"""

    def __init__(self):
        print("🔧 Initializing Model Exporter")

    def export_glb(self, mesh, output_path, image_data=None):
        """
        Export mesh to GLB format (GL Transmission Format Binary)

        Args:
            mesh: Open3D TriangleMesh
            output_path: Path to save GLB file
            image_data: Optional texture image

        Returns:
            success: Boolean
        """
        try:
            print(f"  📦 Exporting GLB to {output_path}")

            # Convert Open3D mesh to trimesh
            vertices = np.asarray(mesh.vertices)
            triangles = np.asarray(mesh.triangles)

            # Get vertex colors if available
            if mesh.has_vertex_colors():
                vertex_colors = np.asarray(mesh.vertex_colors)
                vertex_colors = (vertex_colors * 255).astype(np.uint8)
            else:
                # Default color
                vertex_colors = np.ones((len(vertices), 3), dtype=np.uint8) * 128

            # Create trimesh object
            tri_mesh = trimesh.Trimesh(
                vertices=vertices,
                faces=triangles,
                vertex_colors=vertex_colors,
                process=True
            )

            # Export to GLB
            tri_mesh.export(output_path, file_type='glb')

            print(f"  ✅ GLB exported successfully")
            return True

        except Exception as e:
            print(f"  ❌ Error exporting GLB: {e}")
            return False

    def export_fbx(self, mesh, output_path, image_data=None):
        """
        Export mesh to FBX format

        Args:
            mesh: Open3D TriangleMesh
            output_path: Path to save FBX file
            image_data: Optional texture image

        Returns:
            success: Boolean
        """
        try:
            print(f"  📦 Exporting FBX to {output_path}")

            # Convert Open3D mesh to trimesh
            vertices = np.asarray(mesh.vertices)
            triangles = np.asarray(mesh.triangles)

            # Get vertex colors
            if mesh.has_vertex_colors():
                vertex_colors = np.asarray(mesh.vertex_colors)
                vertex_colors = (vertex_colors * 255).astype(np.uint8)
            else:
                vertex_colors = np.ones((len(vertices), 3), dtype=np.uint8) * 128

            # Create trimesh object
            tri_mesh = trimesh.Trimesh(
                vertices=vertices,
                faces=triangles,
                vertex_colors=vertex_colors,
                process=True
            )

            # Export to FBX
            # Note: trimesh uses assimp for FBX export
            tri_mesh.export(output_path, file_type='fbx')

            print(f"  ✅ FBX exported successfully")
            return True

        except Exception as e:
            print(f"  ❌ Error exporting FBX: {e}")
            print(f"  ⚠️  FBX export may require pyassimp. Exporting as OBJ instead...")

            # Fallback to OBJ if FBX fails
            obj_path = output_path.replace('.fbx', '.obj')
            return self.export_obj(mesh, obj_path, image_data)

    def export_obj(self, mesh, output_path, image_data=None):
        """
        Export mesh to OBJ format (fallback option)

        Args:
            mesh: Open3D TriangleMesh
            output_path: Path to save OBJ file
            image_data: Optional texture image

        Returns:
            success: Boolean
        """
        try:
            print(f"  📦 Exporting OBJ to {output_path}")

            # Open3D has native OBJ export
            o3d.io.write_triangle_mesh(output_path, mesh, write_vertex_colors=True)

            print(f"  ✅ OBJ exported successfully")
            return True

        except Exception as e:
            print(f"  ❌ Error exporting OBJ: {e}")
            return False

    def export_ply(self, mesh, output_path):
        """
        Export mesh to PLY format (for testing/debugging)

        Args:
            mesh: Open3D TriangleMesh
            output_path: Path to save PLY file

        Returns:
            success: Boolean
        """
        try:
            o3d.io.write_triangle_mesh(output_path, mesh, write_vertex_colors=True)
            return True
        except Exception as e:
            print(f"  ❌ Error exporting PLY: {e}")
            return False

    def add_texture_to_mesh(self, mesh, texture_image_path):
        """
        Add texture mapping to mesh

        Args:
            mesh: Open3D TriangleMesh
            texture_image_path: Path to texture image

        Returns:
            mesh: Textured mesh
        """
        try:
            # This is a simplified version
            # Full UV mapping would require proper UV coordinate generation
            # For now, we use vertex colors

            if os.path.exists(texture_image_path):
                texture_image = Image.open(texture_image_path)
                # Process texture...
                pass

            return mesh

        except Exception as e:
            print(f"  ⚠️  Could not add texture: {e}")
            return mesh

    def optimize_for_unity(self, mesh):
        """
        Optimize mesh for Unity import

        Args:
            mesh: Input mesh

        Returns:
            optimized_mesh
        """
        # Unity-specific optimizations
        # - Ensure proper scale
        # - Ensure proper normals
        # - Remove redundant vertices

        mesh.compute_vertex_normals()
        mesh.remove_duplicated_vertices()
        mesh.remove_duplicated_triangles()

        return mesh

    def optimize_for_unreal(self, mesh):
        """
        Optimize mesh for Unreal Engine import

        Args:
            mesh: Input mesh

        Returns:
            optimized_mesh
        """
        # Unreal-specific optimizations
        # Similar to Unity but may have different requirements

        mesh.compute_vertex_normals()
        mesh.remove_duplicated_vertices()
        mesh.remove_duplicated_triangles()

        return mesh
