import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

export function createRotatingPlanet(container, modelUrl, options = {}) {
  const { speed = 0.003, tilt = 0.2, onClick } = options;

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);
  renderer.domElement.style.display = 'block';

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
  camera.position.set(0, 0, 3);

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(5, 2, 5);
  scene.add(sun);

  const pivot = new THREE.Group();
  pivot.rotation.z = tilt;
  scene.add(pivot);

  let model = null;
  new GLTFLoader().load(
    modelUrl,
    (gltf) => {
      model = gltf.scene;
      const box = new THREE.Box3().setFromObject(model);
      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());
      model.position.sub(center);
      model.scale.setScalar(2 / Math.max(size.x, size.y, size.z));
      const box2 = new THREE.Box3().setFromObject(model);
      model.position.sub(box2.getCenter(new THREE.Vector3()));
      pivot.add(model);
    },
    undefined,
    (err) => console.error('Failed to load model:', err)
  );

  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();

  function onClickHandler(event) {
    if (!model) return;
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObject(model, true);

    if (intersects.length > 0) {
      if (onClick) onClick();
    }
  }

  renderer.domElement.addEventListener('click', onClickHandler);

  function resize() {
    const w = container.clientWidth || 1;
    const h = container.clientHeight || 1;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();
  const ro = new ResizeObserver(resize);
  ro.observe(container);

  let frame;
  function animate() {
    frame = requestAnimationFrame(animate);
    pivot.rotation.y += speed;
    renderer.render(scene, camera);
  }
  animate();

  return {
    dispose() {
      cancelAnimationFrame(frame);
      ro.disconnect();
      renderer.domElement.removeEventListener('click', onClickHandler);
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}