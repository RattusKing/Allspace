/**
 * Three.js 3D Model Viewer
 * Renders and allows interaction with generated 3D models
 */

class ModelViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.model = null;
        this.animationId = null;

        this.init();
    }

    init() {
        if (!this.container) {
            console.error('Viewer container not found');
            return;
        }

        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1e293b);
        this.scene.fog = new THREE.Fog(0x1e293b, 10, 50);

        // Create camera
        this.camera = new THREE.PerspectiveCamera(
            75,
            width / height,
            0.1,
            1000
        );
        this.camera.position.set(5, 5, 5);
        this.camera.lookAt(0, 0, 0);

        // Create renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.container.appendChild(this.renderer.domElement);

        // Add orbit controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;
        this.controls.minDistance = 1;
        this.controls.maxDistance = 50;
        this.controls.maxPolarAngle = Math.PI;

        // Add lights
        this.addLights();

        // Add grid helper
        this.addGrid();

        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());

        // Start animation loop
        this.animate();

        console.log('✅ 3D Viewer initialized');
    }

    addLights() {
        // Ambient light for overall illumination
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        // Directional light (sun)
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(5, 10, 5);
        dirLight.castShadow = true;
        dirLight.shadow.camera.top = 10;
        dirLight.shadow.camera.bottom = -10;
        dirLight.shadow.camera.left = -10;
        dirLight.shadow.camera.right = 10;
        dirLight.shadow.camera.near = 0.1;
        dirLight.shadow.camera.far = 40;
        dirLight.shadow.mapSize.width = 2048;
        dirLight.shadow.mapSize.height = 2048;
        this.scene.add(dirLight);

        // Hemisphere light for more natural lighting
        const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.4);
        hemiLight.position.set(0, 20, 0);
        this.scene.add(hemiLight);

        // Add point lights for extra illumination
        const pointLight1 = new THREE.PointLight(0x6366f1, 0.5);
        pointLight1.position.set(-5, 5, -5);
        this.scene.add(pointLight1);

        const pointLight2 = new THREE.PointLight(0x8b5cf6, 0.5);
        pointLight2.position.set(5, 5, 5);
        this.scene.add(pointLight2);
    }

    addGrid() {
        // Add grid helper
        const gridHelper = new THREE.GridHelper(20, 20, 0x4a5568, 0x334155);
        this.scene.add(gridHelper);

        // Add axes helper
        const axesHelper = new THREE.AxesHelper(5);
        this.scene.add(axesHelper);
    }

    loadModel(url) {
        console.log(`📥 Loading 3D model: ${url}`);

        // Remove existing model if any
        if (this.model) {
            this.scene.remove(this.model);
            this.model = null;
        }

        // Show loading indicator
        const loader = new THREE.GLTFLoader();

        loader.load(
            url,
            (gltf) => {
                console.log('✅ Model loaded successfully');
                this.model = gltf.scene;

                // Enable shadows
                this.model.traverse((child) => {
                    if (child.isMesh) {
                        child.castShadow = true;
                        child.receiveShadow = true;

                        // Ensure materials are visible
                        if (child.material) {
                            child.material.needsUpdate = true;
                        }
                    }
                });

                // Center and scale model
                this.centerModel(this.model);

                // Add to scene
                this.scene.add(this.model);

                // Adjust camera to fit model
                this.fitCameraToModel(this.model);

                console.log('🎨 Model added to scene');
            },
            (progress) => {
                const percent = (progress.loaded / progress.total) * 100;
                console.log(`Loading: ${percent.toFixed(2)}%`);
            },
            (error) => {
                console.error('❌ Error loading model:', error);
                this.showErrorMessage();
            }
        );
    }

    centerModel(model) {
        // Calculate bounding box
        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        // Center the model
        model.position.sub(center);

        // Scale model if it's too large or too small
        const maxDim = Math.max(size.x, size.y, size.z);
        if (maxDim > 10) {
            const scale = 10 / maxDim;
            model.scale.multiplyScalar(scale);
        } else if (maxDim < 1) {
            const scale = 2 / maxDim;
            model.scale.multiplyScalar(scale);
        }

        console.log(`Model size: ${size.x.toFixed(2)} x ${size.y.toFixed(2)} x ${size.z.toFixed(2)}`);
    }

    fitCameraToModel(model) {
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());

        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = this.camera.fov * (Math.PI / 180);
        let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));

        cameraZ *= 2; // Add some extra distance

        this.camera.position.set(center.x + cameraZ, center.y + cameraZ, center.z + cameraZ);
        this.camera.lookAt(center);
        this.controls.target.copy(center);
        this.controls.update();
    }

    showErrorMessage() {
        // Add a text sprite showing error
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 512;
        canvas.height = 256;

        context.fillStyle = '#ef4444';
        context.font = 'bold 32px Arial';
        context.textAlign = 'center';
        context.fillText('Error loading model', 256, 128);

        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
        const sprite = new THREE.Sprite(spriteMaterial);
        sprite.scale.set(5, 2.5, 1);
        this.scene.add(sprite);
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());

        // Update controls
        this.controls.update();

        // Rotate model slowly if desired
        // if (this.model) {
        //     this.model.rotation.y += 0.001;
        // }

        // Render scene
        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(width, height);
    }

    dispose() {
        // Clean up
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }

        if (this.renderer) {
            this.renderer.dispose();
            if (this.container && this.renderer.domElement) {
                this.container.removeChild(this.renderer.domElement);
            }
        }

        if (this.controls) {
            this.controls.dispose();
        }

        // Clear scene
        if (this.scene) {
            this.scene.traverse((object) => {
                if (object.geometry) {
                    object.geometry.dispose();
                }
                if (object.material) {
                    if (Array.isArray(object.material)) {
                        object.material.forEach(material => material.dispose());
                    } else {
                        object.material.dispose();
                    }
                }
            });
        }

        console.log('🗑️  Viewer disposed');
    }
}

// Global viewer instance
let viewer = null;

// Function to load model (called from app.js)
function loadModel(url) {
    if (!viewer) {
        viewer = new ModelViewer('viewer3d');
    }
    viewer.loadModel(url);
}

// Expose to global scope
window.viewer = viewer;
window.loadModel = loadModel;
window.ModelViewer = ModelViewer;
