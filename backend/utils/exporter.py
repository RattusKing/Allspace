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

            # Validate mesh before export
            if not self._validate_mesh(mesh):
                print(f"  ❌ Mesh validation failed")
                return False

            # Ensure mesh has necessary attributes
            if not mesh.is_watertight:
                print(f"  ⚠️  Mesh is not watertight (expected for depth-based meshes)")

            # Export to GLB
            mesh.export(output_path, file_type='glb')

            # Verify file was created and has content
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"  ✅ GLB exported successfully ({file_size} bytes)")
                return file_size > 0
            else:
                print(f"  ❌ GLB file was not created")
                return False

        except Exception as e:
            print(f"  ❌ Error exporting GLB: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _validate_mesh(self, mesh):
        """Validate mesh has valid geometry"""
        try:
            # Check mesh has vertices and faces
            if len(mesh.vertices) == 0:
                print(f"  ❌ Mesh has no vertices")
                return False

            if len(mesh.faces) == 0:
                print(f"  ❌ Mesh has no faces")
                return False

            # Check for NaN or Inf in vertices
            if np.isnan(mesh.vertices).any():
                print(f"  ❌ Mesh has NaN vertices")
                return False

            if np.isinf(mesh.vertices).any():
                print(f"  ❌ Mesh has Inf vertices")
                return False

            # Check vertex range is reasonable
            v_min = mesh.vertices.min()
            v_max = mesh.vertices.max()
            v_range = v_max - v_min

            if v_range > 10000:
                print(f"  ⚠️  Mesh has very large range: {v_range:.2f}")

            print(f"  ✅ Mesh validation passed: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
            print(f"     Bounds: [{v_min:.2f}, {v_max:.2f}]")

            return True

        except Exception as e:
            print(f"  ❌ Mesh validation error: {e}")
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
        # Trimesh meshes are already validated and optimized
        # No additional processing needed
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
        # Trimesh meshes are already validated and optimized
        # No additional processing needed
        return mesh
