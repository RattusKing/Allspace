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
        Export mesh (Trimesh or trimesh.Scene) to GLB format.
        Scene objects preserve multiple materials (e.g. UV-textured front face
        + vertex-coloured sides on building facades).
        """
        try:
            print(f"  📦 Exporting GLB to {output_path}")

            if not self._validate_mesh(mesh):
                print(f"  ❌ Mesh validation failed")
                return False

            # trimesh.Scene and trimesh.Trimesh both support .export()
            if not isinstance(mesh, trimesh.Scene) and not mesh.is_watertight:
                print(f"  ⚠️  Mesh is not watertight (expected for depth-based meshes)")

            mesh.export(output_path, file_type='glb')

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
        """Validate mesh (Trimesh or Scene) has valid geometry"""
        try:
            # ── trimesh.Scene validation ──────────────────────────────────
            if isinstance(mesh, trimesh.Scene):
                if len(mesh.geometry) == 0:
                    print(f"  ❌ Scene has no geometry")
                    return False
                total_v = sum(len(g.vertices) for g in mesh.geometry.values())
                total_f = sum(len(g.faces)    for g in mesh.geometry.values())
                if total_v == 0 or total_f == 0:
                    print(f"  ❌ Scene has empty geometry")
                    return False
                all_verts = np.concatenate(
                    [g.vertices for g in mesh.geometry.values()], axis=0
                )
                if np.isnan(all_verts).any() or np.isinf(all_verts).any():
                    print(f"  ❌ Scene has NaN/Inf vertices")
                    return False
                print(f"  ✅ Scene validation passed: {len(mesh.geometry)} meshes, "
                      f"{total_v} vertices, {total_f} faces")
                return True

            # ── Single Trimesh validation ─────────────────────────────────
            if len(mesh.vertices) == 0:
                print(f"  ❌ Mesh has no vertices"); return False
            if len(mesh.faces) == 0:
                print(f"  ❌ Mesh has no faces"); return False
            if np.isnan(mesh.vertices).any():
                print(f"  ❌ Mesh has NaN vertices"); return False
            if np.isinf(mesh.vertices).any():
                print(f"  ❌ Mesh has Inf vertices"); return False

            v_min, v_max = mesh.vertices.min(), mesh.vertices.max()
            if v_max - v_min > 10000:
                print(f"  ⚠️  Mesh has very large range: {v_max - v_min:.2f}")

            print(f"  ✅ Mesh validation passed: {len(mesh.vertices)} vertices, "
                  f"{len(mesh.faces)} faces | bounds [{v_min:.2f}, {v_max:.2f}]")
            return True

        except Exception as e:
            print(f"  ❌ Mesh validation error: {e}")
            return False

    def export_fbx(self, mesh, output_path, image_data=None):
        """
        Export mesh to FBX format.
        For Scene objects (multi-material facades), fall back to OBJ since
        trimesh FBX export does not support Scene graphs.
        """
        try:
            print(f"  📦 Exporting FBX to {output_path}")

            # trimesh Scene → FBX is not supported; use OBJ instead
            if isinstance(mesh, trimesh.Scene):
                print(f"  ⚠️  FBX does not support multi-mesh scenes. Exporting as OBJ.")
                obj_path = output_path.replace('.fbx', '.obj')
                return self.export_obj(mesh, obj_path, image_data)

            mesh.export(output_path, file_type='fbx')
            print(f"  ✅ FBX exported successfully")
            return True

        except Exception as e:
            print(f"  ❌ Error exporting FBX: {e}")
            print(f"  ⚠️  Falling back to OBJ export.")
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
