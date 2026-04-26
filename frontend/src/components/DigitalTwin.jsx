
import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { useNavigate } from 'react-router-dom';
import './DigitalTwin.css';

import { FontLoader } from 'three/addons/loaders/FontLoader.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';

const INSTITUTIONS = [
  { name: 'FSJPST', full: 'Faculté des Sciences Juridiques, Politiques et Sociales de Tunis', status: 'stable', id: 'UCAR-FSJPST' },
  { name: 'FSB', full: 'Faculté des Sciences de Bizerte', status: 'stable', id: 'UCAR-FSB' },
  { name: 'FSEGN', full: 'Faculté des Sciences Economiques et de Gestion de Nabeul', status: 'stable', id: 'UCAR-FSEGN' },
  { name: 'ENAU', full: 'Ecole Nationale d\'Architecture et d\'Urbanisme de Tunis', status: 'warning', id: 'UCAR-ENAU' },
  { name: 'EPT', full: 'Ecole Polytechnique de Tunisie', status: 'stable', id: 'UCAR-EPT' },
  { name: 'ESTI', full: 'Ecole Supérieure de Technologie et d\'Informatique à Carthage', status: 'stable', id: 'UCAR-ESTI' },
  { name: 'ESSAI', full: 'Ecole Supérieure des Statistiques et d\'Analyse de l\'Information', status: 'stable', id: 'UCAR-ESSAI' },
  { name: 'ESAC', full: 'Ecole Supérieure de l\'Audiovisuel et du Cinéma de Gammarth', status: 'stable', id: 'UCAR-ESAC' },
  { name: 'IPEIB', full: 'Institut Préparatoire aux Etudes d\'Ingénieur de Bizerte', status: 'warning', id: 'UCAR-IPEIB' },
  { name: 'IHEC', full: 'Institut des Hautes Etudes Commerciales de Carthage', status: 'stable', id: 'UCAR-IHEC' },
  { name: 'INSAT', full: 'Institut National des Sciences Appliquées et de Technologie', status: 'stable', id: 'UCAR-INSAT' },
  { name: 'ISSATM', full: 'Institut Supérieur des Sciences Appliquées et de la Technologie de Mateur', status: 'stable', id: 'UCAR-ISSATM' },
  { name: 'IPEIN', full: 'Institut Préparatoire aux Etudes d\'Ingénieur Nabeul', status: 'stable', id: 'UCAR-IPEIN' },
  { name: 'IPEST', full: 'Institut Préparatoire aux Etudes Scientifiques et Techniques de la Marsa', status: 'stable', id: 'UCAR-IPEST' },
  { name: 'ISBAN', full: 'Institut Supérieur des Beaux Arts de Nabeul', status: 'critical', id: 'UCAR-ISBAN' },
  { name: 'ISTEUB', full: 'Institut Supérieur des Technologies de l\'Environnement, de L\'Urbanisme et du Bâtiment', status: 'warning', id: 'UCAR-ISTEUB' },
  { name: 'ISLT', full: 'Institut Supérieur des Langues de Tunis', status: 'stable', id: 'UCAR-ISLT' },
  { name: 'ISLAIN', full: 'Institut Supérieur des Langues Appliquées et d\'Informatique de Nabeul', status: 'warning', id: 'UCAR-ISLAIN' },
  { name: 'ISSTE', full: 'Institut Supérieur des Sciences et Technologies de l\'Environnement de Borj Cédria', status: 'stable', id: 'UCAR-ISSTE' },
  { name: 'ISCCB', full: 'Institut Supérieur de Commerce et de Comptabilité de Bizerte', status: 'stable', id: 'UCAR-ISCCB' },
  { name: 'ISEPBG', full: 'Institut Supérieur des Etudes Préparatoires en Biologie et Géologie à Soukra', status: 'stable', id: 'UCAR-ISEPBG' },
  { name: 'SUP\'COM', full: 'Sup\'Com', status: 'stable', id: 'UCAR-SUPCOM' },
  { name: 'ESAM', full: 'Ecole Supérieure d\'Agriculture de Mograne', status: 'warning', id: 'UCAR-ESAM' },
  { name: 'ESAMateur', full: 'Ecole Supérieure d\'Agriculture de Mateur', status: 'warning', id: 'UCAR-ESAMateur' },
  { name: 'ESIAT', full: 'Ecole Supérieure des Industries Alimentaires de Tunis', status: 'stable', id: 'UCAR-ESIAT' },
  { name: 'ISPA', full: 'Institut Supérieur de Pêche et d\'Aquaculture de Bizerte', status: 'stable', id: 'UCAR-ISPA' },
  { name: 'INTES', full: 'Institut National du Travail et des Etudes Sociales de Tunis', status: 'warning', id: 'UCAR-INTES' },
  { name: 'ISCE', full: 'Institut Supérieur des Cadres de l\'Enfance', status: 'stable', id: 'UCAR-ISCE' },
  { name: 'INAT', full: 'Institut National Agronomique de Tunisie', status: 'stable', id: 'UCAR-INAT' },
  { name: 'IHET', full: 'Institut des Hautes Etudes Touristiques de Sidi Dhrif', status: 'stable', id: 'UCAR-IHET' },
  { name: 'INRGREF', full: 'Institut National de Recherche en Génie Rural, Eau et Forêt', status: 'stable', id: 'UCAR-INRGREF' },
  { name: 'INRAT', full: 'Institut National de Recherche Agronomique de Tunis', status: 'stable', id: 'UCAR-INRAT' },
];

export default function DigitalTwin() {
  const mountRef = useRef(null);
  const chartCvsRef = useRef(null);
  const mapCvsRef = useRef(null);
  const tooltipRef = useRef(null);
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [loadText, setLoadText] = useState('Initialising renderer…');
  const [loadPct, setLoadPct] = useState(10);

  const [selectedInst, setSelectedInst] = useState(null);
  const [clockStr, setClockStr] = useState('');
  const [search, setSearch] = useState('');
  const [kpi, setKpi] = useState({ success: 0, budget: 0, ai: 0, staff: 0 });

  // ThreeJS state refs to avoid closure issues in loops
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const clockRef = useRef(null);
  const instMeshes = useRef([]);
  const pulseRings = useRef([]);
  const beams = useRef([]);
  const hubGroupRef = useRef(null);
  const camTweenRef = useRef(null);
  const autoOrbitRef = useRef(true);
  const gridVisibleRef = useRef(true);

  const hoveredIdxRef = useRef(-1);
  const selectedIdxRef = useRef(-1);
  const mouse = useRef(new THREE.Vector2(9, 9));
  const raycaster = new THREE.Raycaster();

  useEffect(() => {
    // Clock interval
    const tId = setInterval(() => {
      setClockStr(new Date().toLocaleTimeString('en-GB'));
    }, 1000);
    return () => clearInterval(tId);
  }, []);

  useEffect(() => {
    if (selectedInst) {
      setKpi({
        success: 55 + Math.random() * 40,
        budget: 30 + Math.random() * 65,
        ai: 50 + Math.random() * 45,
        staff: Math.floor(40 + Math.random() * 260)
      });
      drawChart();
    }
    drawMiniMap();
  }, [selectedInst]);

  useEffect(() => {
    const W = mountRef.current.clientWidth;
    const H = mountRef.current.clientHeight;

    const clock = new THREE.Clock();
    clockRef.current = clock;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f4f8);
    scene.fog = new THREE.Fog(0xf0f4f8, 80, 200);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 500);
    camera.position.set(0, 35, 65);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(W, H);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.3;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    rendererRef.current = renderer;

    mountRef.current.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.minDistance = 15;
    controls.maxDistance = 120;
    controls.maxPolarAngle = Math.PI / 2.1;
    controls.target.set(0, 2, 0);
    controls.autoRotate = true;
    controls.autoRotateSpeed = 1.0;
    controlsRef.current = controls;

    // BUILD ENV
    const ORBIT_R = 42;
    const groundGeo = new THREE.CircleGeometry(100, 64);
    groundGeo.rotateX(-Math.PI / 2);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0xe4e9f0, roughness: 0.9, metalness: 0 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.receiveShadow = true;
    ground.position.y = -0.5;
    scene.add(ground);

    const gridGeo = new THREE.PlaneGeometry(200, 200, 60, 60);
    gridGeo.rotateX(-Math.PI / 2);
    const gridMat = new THREE.MeshBasicMaterial({ color: 0x6b7f9a, wireframe: true, transparent: true, opacity: 0.06 });
    const grid = new THREE.Mesh(gridGeo, gridMat);
    grid.position.y = -0.4;
    grid.name = 'grid';
    scene.add(grid);

    const ringGeo = new THREE.RingGeometry(ORBIT_R - 0.2, ORBIT_R + 0.2, 128);
    ringGeo.rotateX(-Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.15, side: THREE.DoubleSide });
    scene.add(new THREE.Mesh(ringGeo, ringMat));

    // HUB
    setLoadPct(30); setLoadText('Constructing UCAR hub…');
    const hubGroup = new THREE.Group();
    hubGroupRef.current = hubGroup;
    const frameMat = new THREE.MeshPhysicalMaterial({ color: 0x2d3a4e, metalness: 0.7, roughness: 0.2 });
    const base = new THREE.Mesh(new THREE.CylinderGeometry(7, 8, 1.2, 6), frameMat);
    base.castShadow = true;
    hubGroup.add(base);

    const glRing = new THREE.RingGeometry(7.5, 8.8, 64);
    glRing.rotateX(-Math.PI / 2);
    const glMat = new THREE.MeshBasicMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.2, side: THREE.DoubleSide });
    const glMesh = new THREE.Mesh(glRing, glMat);
    glMesh.position.y = 0.08;
    hubGroup.add(glMesh);

    const beacon = new THREE.PointLight(0x3b82f6, 10, 40);
    beacon.position.y = 8;
    hubGroup.add(beacon);
    scene.add(hubGroup);

    // Text loader for UCAR in the middle
    const loader = new FontLoader();
    loader.load('https://cdn.jsdelivr.net/npm/three@0.163.0/examples/fonts/helvetiker_bold.typeface.json', (font) => {
      const textG = new TextGeometry('UCAR', {
        font: font, size: 3.5, depth: 1, curveSegments: 12,
        bevelEnabled: true, bevelThickness: 0.1, bevelSize: 0.05, bevelSegments: 3
      });
      textG.computeBoundingBox();
      const centerOffset = -0.5 * (textG.boundingBox.max.x - textG.boundingBox.min.x);
      const textM = new THREE.MeshPhysicalMaterial({ color: 0x60a5fa, metalness: 0.8, roughness: 0.2, emissive: 0x1e3a8a, emissiveIntensity: 0.5 });
      const textMesh = new THREE.Mesh(textG, textM);
      textMesh.position.set(centerOffset, 2.5, -0.5);
      textMesh.castShadow = true;
      hubGroup.add(textMesh);
    }, undefined, () => {
      // Fallback box if font fails to load
      const boxG = new THREE.BoxGeometry(4, 2, 4);
      const boxM = new THREE.MeshPhysicalMaterial({ color: 0x1e40af });
      const hubCenter = new THREE.Mesh(boxG, boxM);
      hubCenter.position.y = 2;
      hubGroup.add(hubCenter);
    });

    // INSTITUTIONS
    setLoadPct(60); setLoadText('Deploying institutions…');
    const N = INSTITUTIONS.length;
    const statusColors = { stable: 0x16a34a, warning: 0xf59e0b, critical: 0xdc2626 };
    const bodyColors = [0x1e40af, 0x1d4ed8, 0x2563eb, 0x0369a1, 0x4338ca];

    const makeLabel = (text) => {
      const c = document.createElement('canvas');
      c.width = 256; c.height = 48;
      const ctx = c.getContext('2d');
      ctx.font = 'bold 20px sans-serif';
      ctx.fillStyle = '#1e293b';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, 128, 24);
      return new THREE.CanvasTexture(c);
    };

    instMeshes.current = [];
    pulseRings.current = [];
    beams.current = [];

    for (let i = 0; i < N; i++) {
      const inst = INSTITUTIONS[i];
      const angle = (i / N) * Math.PI * 2 - Math.PI / 2;
      const x = Math.cos(angle) * ORBIT_R;
      const z = Math.sin(angle) * ORBIT_R;

      const group = new THREE.Group();
      group.position.set(x, 0, z);

      const h = 4 + Math.random() * 3;
      const geo = new THREE.BoxGeometry(2.5, h, 2.5);
      const sCol = statusColors[inst.status];
      const mat = new THREE.MeshPhysicalMaterial({
        color: bodyColors[i % bodyColors.length], metalness: 0.3, roughness: 0.2,
        clearcoat: 0.6, emissive: sCol, emissiveIntensity: 0.05,
        transparent: true, opacity: 0.88,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.y = h / 2 + 0.5;
      mesh.castShadow = true;
      group.add(mesh);

      const rg = new THREE.RingGeometry(1.8, 2.2, 32);
      rg.rotateX(-Math.PI / 2);
      const rm = new THREE.MeshBasicMaterial({ color: sCol, transparent: true, opacity: 0.25, side: THREE.DoubleSide });
      const ring = new THREE.Mesh(rg, rm);
      ring.position.y = 0.05;
      group.add(ring);

      const lSp = new THREE.Sprite(new THREE.SpriteMaterial({ map: makeLabel(inst.name), transparent: true, depthTest: false }));
      lSp.scale.set(5, 1, 1);
      lSp.position.y = h + 2.5;
      group.add(lSp);

      const prGeo = new THREE.RingGeometry(0.3, 0.5, 32);
      prGeo.rotateX(-Math.PI / 2);
      const prMat = new THREE.MeshBasicMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.5, side: THREE.DoubleSide });
      const pr = new THREE.Mesh(prGeo, prMat);
      pr.position.set(0, 1, 0);
      group.add(pr);

      scene.add(group);
      instMeshes.current.push({ group, mesh, ring, label: lSp, idx: i, baseEmissive: 0.05, status: inst.status, name: inst.name });
      pulseRings.current.push({ mesh: pr, angle, baseX: x, baseZ: z });

      // Beams
      const pts = [new THREE.Vector3(0, 2, 0), new THREE.Vector3(x, 1.5, z)];
      const lineMat = new THREE.LineBasicMaterial({ color: sCol, transparent: true, opacity: 0.15 });
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), lineMat);
      scene.add(line);
      beams.current.push(line);
    }

    setLoadPct(90); setLoadText('Calibrating systems…');
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const sun = new THREE.DirectionalLight(0xffffff, 2.5);
    sun.position.set(40, 60, 30);
    sun.castShadow = true;
    scene.add(sun);
    const fill = new THREE.DirectionalLight(0x93c5fd, 0.6);
    fill.position.set(-30, 20, -30);
    scene.add(fill);

    setTimeout(() => {
      setLoadPct(100);
      setLoadText('System ready.');
      setTimeout(() => setLoading(false), 500);
    }, 500);

    // Event listeners
    const onResize = () => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', onResize);

    const onPointerMove = (e) => {
      if (!mountRef.current) return;
      const rect = mountRef.current.getBoundingClientRect();
      mouse.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse.current, camera);
      const hits = raycaster.intersectObjects(instMeshes.current.map(o => o.mesh), false);
      if (hits.length) {
        const entry = instMeshes.current.find(o => o.mesh === hits[0].object);
        if (entry) {
          hoveredIdxRef.current = entry.idx;
          if (tooltipRef.current) {
            tooltipRef.current.textContent = `${entry.name} - ${entry.status.toUpperCase()}`;
            tooltipRef.current.style.left = e.clientX + 16 + 'px';
            tooltipRef.current.style.top = e.clientY - 10 + 'px';
            tooltipRef.current.classList.add('visible');
          }
          document.body.style.cursor = 'pointer';
          return;
        }
      }
      hoveredIdxRef.current = -1;
      if (tooltipRef.current) tooltipRef.current.classList.remove('visible');
      document.body.style.cursor = 'default';
    };

    const onClick = () => {
      if (hoveredIdxRef.current >= 0) {
        selectedIdxRef.current = hoveredIdxRef.current;
        setSelectedInst(INSTITUTIONS[selectedIdxRef.current]);

        const m = instMeshes.current[selectedIdxRef.current];
        const p = m.group.position;
        // smoothCam
        camTweenRef.current = {
          start: { cx: camera.position.x, cy: camera.position.y, cz: camera.position.z, tx: controls.target.x, ty: controls.target.y, tz: controls.target.z },
          end: { cx: p.x * 0.55, cy: 14, cz: p.z * 0.55, tx: p.x, ty: 4, tz: p.z },
          elapsed: 0, dur: 1.4
        };
      }
    };

    renderer.domElement.addEventListener('pointermove', onPointerMove);
    renderer.domElement.addEventListener('click', onClick);

    // Animation Loop
    let reqId;
    const animate = () => {
      reqId = requestAnimationFrame(animate);
      const dt = clock.getDelta();
      const t = clock.getElapsedTime();

      if (selectedIdxRef.current < 0 && !camTweenRef.current) {
        controls.autoRotate = autoOrbitRef.current;
      } else {
        controls.autoRotate = false;
      }

      if (camTweenRef.current) {
        const ct = camTweenRef.current;
        ct.elapsed += dt;
        let v = Math.min(ct.elapsed / ct.dur, 1);
        v = v < 0.5 ? 4 * v * v * v : 1 - Math.pow(-2 * v + 2, 3) / 2;
        camera.position.lerpVectors(new THREE.Vector3(ct.start.cx, ct.start.cy, ct.start.cz), new THREE.Vector3(ct.end.cx, ct.end.cy, ct.end.cz), v);
        controls.target.lerpVectors(new THREE.Vector3(ct.start.tx, ct.start.ty, ct.start.tz), new THREE.Vector3(ct.end.tx, ct.end.ty, ct.end.tz), v);
        if (v >= 1) camTweenRef.current = null;
      }

      controls.update();

      instMeshes.current.forEach((o, i) => {
        o.group.position.y = Math.sin(t * 0.6 + i * 0.5) * 0.25;
        const isSel = i === selectedIdxRef.current || i === hoveredIdxRef.current;
        o.mesh.material.emissiveIntensity += ((isSel ? 0.35 : o.baseEmissive) - o.mesh.material.emissiveIntensity) * 0.1;
        o.ring.material.opacity = isSel ? 0.55 : 0.2;
        o.label.material.opacity = isSel ? 1 : 0.65;
      });

      beams.current.forEach((b, i) => {
        b.material.opacity = 0.1 + Math.sin(t * 1.5 + i * 0.4) * 0.07;
      });

      pulseRings.current.forEach((pr, i) => {
        const cycle = (t * 0.4 + i * 0.1) % 1;
        pr.mesh.position.set(pr.baseX * cycle - pr.baseX, 1.5, pr.baseZ * cycle - pr.baseZ);
        const s = 0.5 + cycle * 1.5;
        pr.mesh.scale.set(s, s, s);
        pr.mesh.material.opacity = (1 - cycle) * 0.4;
      });

      // Handle search visual filtering
      if (search) {
        const query = search.toLowerCase();
        instMeshes.current.forEach((o) => {
          const isMatch = o.name.toLowerCase().includes(query) || INSTITUTIONS[o.idx].full.toLowerCase().includes(query);
          if (!isMatch) {
            o.mesh.material.opacity = 0.15;
            o.ring.material.opacity = 0.05;
            o.label.material.opacity = 0.2;
          } else {
            o.mesh.material.opacity = 0.88;
            o.ring.material.opacity = 0.25;
            o.label.material.opacity = 0.65;
          }
        });
      } else {
        instMeshes.current.forEach((o, i) => {
          const isSel = i === selectedIdxRef.current || i === hoveredIdxRef.current;
          o.mesh.material.opacity = 0.88;
          if (!isSel) {
            o.ring.material.opacity = 0.2;
            o.label.material.opacity = 0.65;
          }
        });
      }

      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(reqId);
      window.removeEventListener('resize', onResize);
      if (mountRef.current && renderer.domElement) mountRef.current.removeChild(renderer.domElement);
      renderer.dispose();
      scene.clear();
      document.body.style.cursor = 'default';
    };
  }, []);

  const drawChart = () => {
    if (!chartCvsRef.current) return;
    const ctx = chartCvsRef.current.getContext('2d');
    const W = chartCvsRef.current.width, H = chartCvsRef.current.height;
    ctx.clearRect(0, 0, W, H);
    const pts = Array.from({ length: 12 }, () => 0.2 + Math.random() * 0.6);
    const grad = ctx.createLinearGradient(0, 0, W, 0);
    grad.addColorStop(0, '#1e40af'); grad.addColorStop(1, '#3b82f6');
    ctx.beginPath();
    pts.forEach((v, i) => {
      const x = (i / (pts.length - 1)) * W;
      const y = H - v * H;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = grad; ctx.lineWidth = 2; ctx.stroke();
    ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
    const gf = ctx.createLinearGradient(0, 0, 0, H);
    gf.addColorStop(0, 'rgba(59,130,246,.15)'); gf.addColorStop(1, 'rgba(59,130,246,0)');
    ctx.fillStyle = gf; ctx.fill();
  };

  const drawMiniMap = () => {
    if (!mapCvsRef.current) return;
    const ctx = mapCvsRef.current.getContext('2d');
    const W = mapCvsRef.current.width, H = mapCvsRef.current.height;
    const cx = W / 2, cy = H / 2, r = 52;
    ctx.clearRect(0, 0, W, H);
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(59,130,246,.25)'; ctx.lineWidth = 1; ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#1e40af'; ctx.fill();
    INSTITUTIONS.forEach((inst, i) => {
      const a = (i / INSTITUTIONS.length) * Math.PI * 2 - Math.PI / 2;
      const x = cx + Math.cos(a) * r;
      const y = cy + Math.sin(a) * r;
      const col = inst.status === 'critical' ? '#dc2626' : inst.status === 'warning' ? '#f59e0b' : '#16a34a';
      ctx.beginPath(); ctx.arc(x, y, i === selectedIdxRef.current ? 4 : 2.5, 0, Math.PI * 2);
      ctx.fillStyle = col; ctx.fill();
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(x, y);
      ctx.strokeStyle = 'rgba(59,130,246,.12)'; ctx.lineWidth = 0.5; ctx.stroke();
    });
  };

  const resetCamera = () => {
    selectedIdxRef.current = -1;
    setSelectedInst(null);
    camTweenRef.current = {
      start: { cx: cameraRef.current.position.x, cy: cameraRef.current.position.y, cz: cameraRef.current.position.z, tx: controlsRef.current.target.x, ty: controlsRef.current.target.y, tz: controlsRef.current.target.z },
      end: { cx: 0, cy: 35, cz: 65, tx: 0, ty: 2, tz: 0 },
      elapsed: 0, dur: 1.4
    };
  };

  const toggleOrbit = () => {
    autoOrbitRef.current = !autoOrbitRef.current;
  };

  const toggleGrid = () => {
    gridVisibleRef.current = !gridVisibleRef.current;
    const g = sceneRef.current.getObjectByName('grid');
    if (g) g.visible = gridVisibleRef.current;
  };

  const doDeepDive = () => {
    if (selectedInst) {
      navigate(`/institution?id=${selectedInst.id}`);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (!search.trim()) return;
    const query = search.toLowerCase().trim();
    const idx = INSTITUTIONS.findIndex(inst => inst.name.toLowerCase().includes(query) || inst.full.toLowerCase().includes(query));
    if (idx >= 0 && instMeshes.current[idx]) {
      selectedIdxRef.current = idx;
      setSelectedInst(INSTITUTIONS[idx]);

      const m = instMeshes.current[idx];
      const p = m.group.position;
      camTweenRef.current = {
        start: { cx: cameraRef.current.position.x, cy: cameraRef.current.position.y, cz: cameraRef.current.position.z, tx: controlsRef.current.target.x, ty: controlsRef.current.target.y, tz: controlsRef.current.target.z },
        end: { cx: p.x * 0.55, cy: 14, cz: p.z * 0.55, tx: p.x, ty: 4, tz: p.z },
        elapsed: 0, dur: 1.4
      };
    } else {
      alert("Établissement non trouvé.");
    }
  };

  return (
    <div className="dt-container animate-fade">
      {loading && (
        <div className="dt-loader">
          <div className="loader-inner">
            <div className="loader-logo">
              <span className="logo-u">U</span><span class="logo-c">C</span><span class="logo-a">A</span><span class="logo-r">R</span>
            </div>
            <p className="loader-sub">DIGITAL TWIN METAVERSE</p>
            <div className="loader-bar-wrap"><div className="loader-bar" style={{ width: loadPct + '%' }}></div></div>
            <p className="loader-status">{loadText}</p>
          </div>
        </div>
      )}

      <header className="hud-top">
        <div className="hud-brand">
          <span className="brand-icon">⬡</span>
          <span className="brand-text">UCAR <em>Digital Twin</em></span>
        </div>
        <div className="hud-stats hidden sm:flex">
          <div className="stat-pill"><span className="dt-dot green"></span>32 Institutions</div>
          <div className="stat-pill"><span className="dt-dot cyan"></span>Live Sync</div>
          <div className="stat-pill">{clockStr}</div>
        </div>
        <form onSubmit={handleSearchSubmit} className="hud-search mx-auto max-w-md w-full px-4 hidden md:flex items-center gap-2">
          <input
            type="text"
            placeholder="Rechercher un établissement (ex: INSAT)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 bg-white/10 border border-white/20 rounded-full py-1.5 px-4 text-white placeholder-blue-200/50 text-sm focus:outline-none focus:border-blue-400 focus:bg-white/20 backdrop-blur-md transition-all"
          />
          <button type="submit" className="hud-btn" style={{ padding: '6px 12px', borderRadius: '20px' }}>🔍</button>
        </form>
        <div className="hud-controls ml-auto shrink-0">
          <button className="hud-btn" onClick={toggleOrbit}>⟳ ORBIT</button>
          <button className="hud-btn" onClick={resetCamera}>⌖ RESET</button>
          <button className="hud-btn" onClick={toggleGrid}>⊞ GRID</button>
        </div>
      </header>

      <div className="dt-canvas" ref={mountRef}></div>

      {/* INFO PANEL */}
      <aside className={`dt-info-panel ${!selectedInst ? 'hidden' : ''}`}>
        {selectedInst && (
          <>
            <div className="panel-header">
              <div className="panel-icon">🏛</div>
              <div>
                <div className="panel-title">{selectedInst.name}</div>
                <div className="panel-sub">{selectedInst.full}</div>
              </div>
              <button className="panel-close" onClick={() => { selectedIdxRef.current = -1; setSelectedInst(null); }}>✕</button>
            </div>
            <div className="panel-status-row">
              <span className={`status-badge ${selectedInst.status}`}>{selectedInst.status.toUpperCase()}</span>
              <span className="panel-id">NODE-{String(INSTITUTIONS.indexOf(selectedInst) + 1).padStart(2, '0')}</span>
            </div>
            <div className="kpi-grid">
              <div className="kpi-card">
                <div className="kpi-label">Success Rate</div>
                <div className="kpi-value">{kpi.success.toFixed(1)}%</div>
                <div className="kpi-bar"><div className="kpi-fill cyan" style={{ width: kpi.success + '%' }}></div></div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Budget Usage</div>
                <div className="kpi-value">{kpi.budget.toFixed(1)}%</div>
                <div className="kpi-bar"><div className="kpi-fill blue" style={{ width: kpi.budget + '%' }}></div></div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">AI Prediction</div>
                <div className="kpi-value">{kpi.ai.toFixed(1)}%</div>
                <div className="kpi-bar"><div className="kpi-fill purple" style={{ width: kpi.ai + '%' }}></div></div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Staff Count</div>
                <div className="kpi-value">{kpi.staff}</div>
                <div className="kpi-bar"><div className="kpi-fill green" style={{ width: Math.min(kpi.staff / 3, 100) + '%' }}></div></div>
              </div>
            </div>
            <div className="panel-chart-label">Performance Trend</div>
            <canvas ref={chartCvsRef} className="mini-chart" width="260" height="80"></canvas>
            <div className="panel-footer">
              <button className="panel-btn" onClick={doDeepDive}>⬡ Deep Dive</button>
              <button className="panel-btn outline" onClick={resetCamera}>← Back</button>
            </div>
          </>
        )}
      </aside>

      <div className="mini-map">
        <canvas ref={mapCvsRef} className="map-canvas" width="140" height="140"></canvas>
        <div className="map-label">NETWORK MAP</div>
      </div>

      <div className="dt-legend">
        <div className="leg-item"><span className="dt-dot green"></span>Stable</div>
        <div className="leg-item"><span className="dt-dot yellow"></span>Warning</div>
        <div className="leg-item"><span className="dt-dot red"></span>Critical</div>
      </div>

      <div className="dt-tooltip" ref={tooltipRef}></div>
    </div>
  );
}
