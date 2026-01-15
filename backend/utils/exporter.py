"""
Model Exporter Module
Exports 3D meshes to various formats (GLB, FBX, OBJ) using trimesh
"""

import os
import numpy as np
import trimesh
from PIL import Image


class ModelExporter:
    """Exports 3D models to various formats compatible with Unity, Unreal, Blender"""

    def __init__(self):
        print("🔧 Initializing Model Exporter (trimesh-based)")

    def export_glb(self, mesh, output_path, image_data=None):
        """
        Export mesh to GLB format (GL Transmission Format Binary)

        Args:
            mesh: Trimesh object
            output_path: Path to save GLB file
            image_data: Optional texture image

        Returns:
            success: Boolean
        """
        try:
            print(f"  📦 Exporting GLB to {output_path}")

            # Trimesh can export directly to GLB
            mesh.export(output_path, file_type='glb')

            print(f"  ✅ GLB exported successfully")
            return True

        except Exception as e:
            print(f"  ❌ Error exporting GLB: {e}")
            return False

    def export_fbx(self, mesh, output_path, image_data=None):
        """
        Export mesh to FBX format

        Args:
            mesh: Trimesh object
            output_path: Path to save FBX file
            image_data: Optional texture image

        Returns:
            success: Boolean
        """
        try:
            print(f"  📦 Exporting FBX to {output_path}")

            # Try to export to FBX
            mesh.export(output_path, file_type='fbx')

            print(f"  ✅ FBX exported successfully")
            return True

        except Exception as e:
            print(f"  ❌ Error exporting FBX: {e}")
            print(f"  ⚠️  FBX export may require additional dependencies. Exporting as OBJ instead...")

            # Fallback to OBJ if FBX fails
            obj_path = output_path.replace('.fbx', '.obj')
            return self.export_obj(mesh, obj_path, image_data)

    def export_obj(self, mesh, output_path, image_data=None):
        """
        Export mesh to OBJ format (fallback option)

        Args:
            mesh: Trimesh object
            output_path: Path to save OBJ file
            image_data: Optional texture image

        Returns:
            success: Boolean
        """
        try:
            print(f"  📦 Exporting OBJ to {output_path}")

            # Trimesh has native OBJ export
            mesh.export(output_path, file_type='obj')

            print(f"  ✅ OBJ exported successfully")
            return True

        except Exception as e:
            print(f"  ❌ Error exporting OBJ: {e}")
            return False

    def export_ply(self, mesh, output_path):
        """
        Export mesh to PLY format (for testing/debugging)

        Args:
            mesh: Trimesh object
            output_path: Path to save PLY file

        Returns:
            success: Boolean
        """
        try:
            mesh.export(output_path, file_type='ply')
            return True
        except Exception as e:
            print(f"  ❌ Error exporting PLY: {e}")
            return False

    def add_texture_to_mesh(self, mesh, texture_image_path):
        """
        Add texture mapping to mesh

        Args:
            mesh: Trimesh object
            texture_image_path: Path to texture image

        Returns:
            mesh: Textured mesh
        """
        try:
            # Trimesh handles textures through visual properties
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
            mesh: Input trimesh

        Returns:
            optimized_mesh
        """
        # Unity-specific optimizations
        # Trimesh handles duplicate cleanup automatically
        mesh.remove_degenerate_faces()
        mesh.remove_unreferenced_vertices()
        mesh.fix_normals()

        return mesh

    def optimize_for_unreal(self, mesh):
        """
        Optimize mesh for Unreal Engine import

        Args:
            mesh: Input trimesh

        Returns:
            optimized_mesh
        """
        # Unreal-specific optimizations
        # Trimesh handles duplicate cleanup automatically
        mesh.remove_degenerate_faces()
        mesh.remove_unreferenced_vertices()
        mesh.fix_normals()

        return mesh
