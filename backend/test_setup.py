#!/usr/bin/env python3
"""
Setup verification script
Tests that all dependencies are correctly installed
"""

import sys

def test_imports():
    """Test that all required packages can be imported"""
    print("🧪 Testing package imports...")
    
    packages = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'cv2': 'OpenCV',
        'PIL': 'Pillow',
        'trimesh': 'Trimesh',
        'numpy': 'NumPy',
        'scipy': 'SciPy',
        'networkx': 'NetworkX',
    }
    
    failed = []
    
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError as e:
            print(f"  ❌ {name}: {e}")
            failed.append(name)
    
    if failed:
        print(f"\n❌ Failed to import: {', '.join(failed)}")
        print("Run: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All packages imported successfully!")
        return True

def test_directories():
    """Test that required directories exist"""
    print("\n📁 Checking directories...")
    
    import os
    
    dirs = ['uploads', 'outputs', 'models', 'utils']
    
    for dir_name in dirs:
        if os.path.isdir(dir_name):
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ not found")
    
    print("✅ Directory check complete!")

def main():
    print("=" * 50)
    print("Allspace - Setup Verification")
    print("=" * 50)

    if not test_imports():
        sys.exit(1)

    test_directories()

    print("\n" + "=" * 50)
    print("🎉 Setup verification complete!")
    print("=" * 50)
    print("\nYou can now run: python app.py")

if __name__ == '__main__':
    main()
