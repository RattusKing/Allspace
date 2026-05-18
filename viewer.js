/**
 * Three.js 3D Model Viewer
 * Renders and allows interaction with generated 3D models.
 * Supports Orbit mode (default) and first-person Walk mode (WASD + mouse look).
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

        // Walk mode state
        this.walkMode = false;
        this.walkYaw = 0;
        this.walkPitch = 0;
        this.walkKeys = {};
        this.walkSpeed = 3.0;
        this.prevFrameTime = performance.now();

        this._boundMouseMove = this._onMouseMoveWalk.bind(this);
        this._boundPointerLockChange = this._onPointerLockChange.bind(this);
        this._boundKeyDown = (e) => { this.walkKeys[e.code] = true; };
        this._boundKeyUp = (e) => { this.walkKeys[e.code] = false; };

        this.init();
    }

    init() {
        if (!this.container) {
            console.error('Viewer container not found');
            return;
        }

        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1e293b);
        this.scene.fog = new THREE.Fog(0x1e293b, 10, 50);

        // Camera
        this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        this.camera.position.set(5, 5, 5);
        this.camera.lookAt(0, 0, 0);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        if (THREE.SRGBColorSpace !== undefined) {
            this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        } else if (THREE.sRGBEncoding !== undefined) {
            this.renderer.outputEncoding = THREE.sRGBEncoding;
        }
        this.container.appendChild(this.renderer.domElement);

        // Orbit controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;
        this.controls.minDistance = 0.5;
        this.controls.maxDistance = 50;
        this.controls.maxPolarAngle = Math.PI;

        this.addLights();
        this.addGrid();

        // Global event listeners for walk mode
        document.addEventListener('mousemove', this._boundMouseMove);
        document.addEventListener('pointerlockchange', this._boundPointerLockChange);
        document.addEventListener('keydown', this._boundKeyDown);
        document.addEventListener('keyup', this._boundKeyUp);

        window.addEventListener('resize', () => this.onWindowResize());

        this.animate();
        console.log('✅ 3D Viewer initialized');
    }

    addLights() {
        const ambientLight = new THREE.AmbientLight(0xffffff, 1.0);
        this.scene.add(ambientLight);

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

        const fillLight = new THREE.DirectionalLight(0xffffff, 0.4);
        fillLight.position.set(-5, 5, -5);
        this.scene.add(fillLight);

        const hemiLight = new THREE.HemisphereLight(0xffffff, 0xcccccc, 0.3);
        hemiLight.position.set(0, 20, 0);
        this.scene.add(hemiLight);
    }

    addGrid() {
        const gridHelper = new THREE.GridHelper(20, 20, 0x4a5568, 0x334155);
        this.scene.add(gridHelper);

        const axesHelper = new THREE.AxesHelper(5);
        this.scene.add(axesHelper);
    }

    loadModel(url) {
        console.log(`📥 Loading 3D model: ${url}`);

        if (this.model) {
            this.scene.remove(this.model);
            this.model = null;
        }

        const loader = new THREE.GLTFLoader();
        loader.load(
            url,
            (gltf) => {
                console.log('✅ Model loaded successfully');
                this.model = gltf.scene;

                this.model.traverse((child) => {
                    if (child.isMesh) {
                        child.castShadow = true;
                        child.receiveShadow = true;

                        if (child.material) {
                            child.material.side = THREE.DoubleSide;

                            if (child.geometry && child.geometry.attributes.color) {
                                child.material.vertexColors = true;
                            }

                            if (child.material.map) {
                                if (THREE.SRGBColorSpace !== undefined) {
                                    child.material.map.colorSpace = THREE.SRGBColorSpace;
                                } else if (THREE.sRGBEncoding !== undefined) {
                                    child.material.map.encoding = THREE.sRGBEncoding;
                                }
                            }

                            child.material.needsUpdate = true;
                        }
                    }
                });

                this.centerModel(this.model);
                this.scene.add(this.model);
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
        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        model.position.sub(center);

        const maxDim = Math.max(size.x, size.y, size.z);
        if (maxDim > 10) {
            model.scale.multiplyScalar(10 / maxDim);
        } else if (maxDim < 1) {
            model.scale.multiplyScalar(2 / maxDim);
        }

        console.log(`Model size: ${size.x.toFixed(2)} x ${size.y.toFixed(2)} x ${size.z.toFixed(2)}`);
    }

    fitCameraToModel(model) {
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());

        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = this.camera.fov * (Math.PI / 180);
        const cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2)) * 2;

        this.camera.position.set(center.x + cameraZ, center.y + cameraZ, center.z + cameraZ);
        this.camera.lookAt(center);
        this.controls.target.copy(center);
        this.controls.update();
    }

    // ── Walk Mode ─────────────────────────────────────────────────────────────

    toggleWalkMode() {
        if (!this.walkMode) {
            this._enterWalkMode();
        } else {
            this._exitWalkMode();
        }
    }

    _enterWalkMode() {
        this.walkMode = true;
        this.controls.enabled = false;

        // Position camera at eye height above the model floor
        if (this.model) {
            const box = new THREE.Box3().setFromObject(this.model);
            this.camera.position.y = box.min.y + 1.6;
        }

        // Derive initial yaw from current camera orientation
        const dir = new THREE.Vector3();
        this.camera.getWorldDirection(dir);
        this.walkYaw = Math.atan2(-dir.x, -dir.z);
        this.walkPitch = 0;

        this.camera.rotation.order = 'YXZ';
        this.camera.rotation.y = this.walkYaw;
        this.camera.rotation.x = this.walkPitch;

        // Request pointer lock so mouse controls look direction
        this.renderer.domElement.requestPointerLock();

        this._setWalkUI(true);
    }

    _exitWalkMode() {
        this.walkMode = false;
        this.controls.enabled = true;
        this.walkKeys = {};

        if (document.pointerLockElement === this.renderer.domElement) {
            document.exitPointerLock();
        }

        this._setWalkUI(false);
    }

    _setWalkUI(active) {
        const btn = document.getElementById('walkToggleBtn');
        const hint = document.getElementById('viewerHint');
        const crosshair = document.getElementById('walkCrosshair');

        if (active) {
            if (btn) { btn.textContent = '🚶 Exit Walk'; btn.classList.add('active'); }
            if (hint) hint.textContent = 'WASD: Move • Mouse: Look • Space/Shift: Up/Down • ESC: Exit';
            if (crosshair) crosshair.classList.remove('hidden');
        } else {
            if (btn) { btn.textContent = '🚶 Walk Mode'; btn.classList.remove('active'); }
            if (hint) hint.textContent = '🖱️ Left-click + drag: Rotate • Right-click + drag: Pan • Scroll: Zoom';
            if (crosshair) crosshair.classList.add('hidden');
        }
    }

    _onPointerLockChange() {
        // Browser releases pointer lock on ESC — exit walk mode to stay in sync
        if (document.pointerLockElement !== this.renderer.domElement && this.walkMode) {
            this._exitWalkMode();
        }
    }

    _onMouseMoveWalk(e) {
        if (!this.walkMode || document.pointerLockElement !== this.renderer.domElement) return;

        const sensitivity = 0.002;
        this.walkYaw -= e.movementX * sensitivity;
        this.walkPitch -= e.movementY * sensitivity;
        // Clamp pitch so you can't flip upside down
        this.walkPitch = Math.max(-Math.PI / 2 + 0.05, Math.min(Math.PI / 2 - 0.05, this.walkPitch));

        this.camera.rotation.y = this.walkYaw;
        this.camera.rotation.x = this.walkPitch;
    }

    _updateWalkMovement(dt) {
        // Get flattened forward vector (ignore Y so moving forward doesn't pitch down)
        const camDir = new THREE.Vector3();
        this.camera.getWorldDirection(camDir);
        const forward = new THREE.Vector3(camDir.x, 0, camDir.z).normalize();
        const right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize();

        const speed = this.walkSpeed;
        const move = new THREE.Vector3();

        if (this.walkKeys['KeyW'] || this.walkKeys['ArrowUp'])    move.addScaledVector(forward,  speed * dt);
        if (this.walkKeys['KeyS'] || this.walkKeys['ArrowDown'])  move.addScaledVector(forward, -speed * dt);
        if (this.walkKeys['KeyA'] || this.walkKeys['ArrowLeft'])  move.addScaledVector(right,   -speed * dt);
        if (this.walkKeys['KeyD'] || this.walkKeys['ArrowRight']) move.addScaledVector(right,    speed * dt);
        if (this.walkKeys['Space'])                               move.y += speed * dt;
        if (this.walkKeys['ShiftLeft'] || this.walkKeys['ShiftRight']) move.y -= speed * dt;

        this.camera.position.add(move);
    }

    // ── Render Loop ───────────────────────────────────────────────────────────

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());

        const now = performance.now();
        const dt = Math.min((now - this.prevFrameTime) / 1000, 0.1); // cap delta to avoid jumps
        this.prevFrameTime = now;

        if (this.walkMode) {
            this._updateWalkMovement(dt);
        } else {
            this.controls.update();
        }

        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    showErrorMessage() {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 512;
        canvas.height = 256;
        context.fillStyle = '#ef4444';
        context.font = 'bold 32px Arial';
        context.textAlign = 'center';
        context.fillText('Error loading model', 256, 128);

        const texture = new THREE.CanvasTexture(canvas);
        const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture }));
        sprite.scale.set(5, 2.5, 1);
        this.scene.add(sprite);
    }

    dispose() {
        if (this.walkMode) this._exitWalkMode();

        document.removeEventListener('mousemove', this._boundMouseMove);
        document.removeEventListener('pointerlockchange', this._boundPointerLockChange);
        document.removeEventListener('keydown', this._boundKeyDown);
        document.removeEventListener('keyup', this._boundKeyUp);

        if (this.animationId) cancelAnimationFrame(this.animationId);

        if (this.renderer) {
            this.renderer.dispose();
            if (this.container && this.renderer.domElement) {
                this.container.removeChild(this.renderer.domElement);
            }
        }

        if (this.controls) this.controls.dispose();

        if (this.scene) {
            this.scene.traverse((object) => {
                if (object.geometry) object.geometry.dispose();
                if (object.material) {
                    if (Array.isArray(object.material)) {
                        object.material.forEach(m => m.dispose());
                    } else {
                        object.material.dispose();
                    }
                }
            });
        }

        console.log('🗑️  Viewer disposed');
    }
}

// ── Global API ────────────────────────────────────────────────────────────────

let viewer = null;

function loadModel(url) {
    if (!viewer) {
        viewer = new ModelViewer('viewer3d');
    }
    viewer.loadModel(url);
}

function toggleWalkMode() {
    if (viewer) viewer.toggleWalkMode();
}

window.viewer = viewer;
window.loadModel = loadModel;
window.toggleWalkMode = toggleWalkMode;
window.ModelViewer = ModelViewer;
