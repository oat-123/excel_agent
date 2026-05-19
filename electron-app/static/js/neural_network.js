// Neural Network Visualization - J.A.R.V.I.S. Core
// This is the brain 3D visualization sidebar

let scene, camera, renderer, controls
let nodes = [], connections = []
let clock = new THREE.Clock()

function initNeuralNetwork() {
  const container = document.getElementById('canvas-container')

  // Scene
  scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x02040a, 0.0008)

  // Camera
  camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 5000)
  camera.position.set(0, 150, 400)
  camera.lookAt(0, 0, 0)

  // Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  container.appendChild(renderer.domElement)

  // Controls
  controls = new THREE.OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.rotateSpeed = 0.5
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.3
  controls.minDistance = 200
  controls.maxDistance = 800

  // Light
  const ambientLight = new THREE.AmbientLight(0x111122, 0.5)
  scene.add(ambientLight)
  const pointLight = new THREE.PointLight(0x00f2ff, 1, 1000)
  pointLight.position.set(200, 200, 200)
  scene.add(pointLight)

  // Create Neural Core (central sphere)
  createCore()

  // Create orbital nodes
  createNodes(80)

  // Create connecting lines
  createConnections()

  // Add particles
  addParticles()

  // Events
  window.addEventListener('resize', onWindowResize)
  document.getElementById('neural-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') processNeuralCommand()
  })

  animate()
}

function createCore() {
  const geometry = new THREE.IcosahedronGeometry(40, 2)
  const material = new THREE.MeshPhongMaterial({
    color: 0x00f2ff,
    emissive: 0x00f2ff,
    emissiveIntensity: 0.3,
    transparent: true,
    opacity: 0.8,
    wireframe: false
  })
  const core = new THREE.Mesh(geometry, material)
  scene.add(core)

  // Outer wireframe shell
  const wireframe = new THREE.LineSegments(
    new THREE.WireframeGeometry(geometry),
    new THREE.LineBasicMaterial({ color: 0x00f2ff, transparent: true, opacity: 0.3 })
  )
  core.add(wireframe)
}

function createNodes(count) {
  const colors = [0x00f2ff, 0x8a2be2, 0x00ff6a, 0xff3366]

  for (let i = 0; i < count; i++) {
    const group = new THREE.Group()

    // Node sphere
    const geometry = new THREE.SphereGeometry(3 + Math.random() * 4, 16, 16)
    const color = colors[Math.floor(Math.random() * colors.length)]
    const material = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.7
    })
    const sphere = new THREE.Mesh(geometry, material)
    group.add(sphere)

    // Glow halo
    const glowGeo = new THREE.SphereGeometry(6, 16, 16)
    const glowMat = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.15
    })
    const glow = new THREE.Mesh(glowGeo, glowMat)
    group.add(glow)

    // Position on sphere surface
    const phi = Math.acos(2 * Math.random() - 1)
    const theta = Math.random() * Math.PI * 2
    const radius = 150 + Math.random() * 100
    group.position.setFromSphericalCoords(radius, phi, theta)

    // Random orbit direction
    group.userData = {
      orbitAxis: new THREE.Vector3(Math.random(), Math.random(), Math.random()).normalize(),
      orbitSpeed: 0.1 + Math.random() * 0.3,
      phase: Math.random() * Math.PI * 2
    }

    nodes.push(group)
    scene.add(group)
  }
}

function createConnections() {
  const material = new THREE.LineBasicMaterial({
    color: 0x00f2ff,
    transparent: true,
    opacity: 0.15
  })

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dist = nodes[i].position.distanceTo(nodes[j].position)
      if (dist < 180) {
        const geometry = new THREE.BufferGeometry().setFromPoints([
          nodes[i].position,
          nodes[j].position
        ])
        const line = new THREE.Line(geometry, material)
        connections.push({ line, from: i, to: j })
        scene.add(line)
      }
    }
  }
}

function addParticles() {
  const particleCount = 500
  const geometry = new THREE.BufferGeometry()
  const positions = new Float32Array(particleCount * 3)

  for (let i = 0; i < particleCount * 3; i += 3) {
    positions[i] = (Math.random() - 0.5) * 800
    positions[i+1] = (Math.random() - 0.5) * 800
    positions[i+2] = (Math.random() - 0.5) * 800
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

  const material = new THREE.PointsMaterial({
    color: 0x00f2ff,
    size: 1.5,
    transparent: true,
    opacity: 0.4
  })

  const particles = new THREE.Points(geometry, material)
  scene.add(particles)
}

function animate() {
  requestAnimationFrame(animate)
  const delta = clock.getDelta()
  const time = clock.getElapsedTime()

  // Rotate nodes
  nodes.forEach((node, idx) => {
    const data = node.userData
    node.rotateOnAxis(data.orbitAxis, data.orbitSpeed * delta)
  })

  // Update connections
  connections.forEach(conn => {
    const positions = conn.line.geometry.attributes.position.array
    positions[0] = nodes[conn.from].position.x
    positions[1] = nodes[conn.from].position.y
    positions[2] = nodes[conn.from].position.z
    positions[3] = nodes[conn.to].position.x
    positions[4] = nodes[conn.to].position.y
    positions[5] = nodes[conn.to].position.z
    conn.line.geometry.attributes.position.needsUpdate = true
  })

  // Core pulse
  const scale = 1 + Math.sin(time * 2) * 0.05
  if (scene.children[0]) {
    scene.children[0].scale.setScalar(scale)
  }

  controls.update()
  renderer.render(scene, camera)
}

function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight
  camera.updateProjectionMatrix()
  renderer.setSize(window.innerWidth, window.innerHeight)
}

function zoomToCore() {
  const duration = 2000
  const startPos = camera.position.clone()
  const endPos = new THREE.Vector3(0, 0, 150)
  const startTime = Date.now()
  
  function tween() {
    const elapsed = Date.now() - startTime
    const t = Math.min(elapsed / duration, 1)
    // Ease out cubic
    const eased = 1 - Math.pow(1 - t, 3)
    
    camera.position.lerpVectors(startPos, endPos, eased)
    controls.update()
    
    if (t < 1) requestAnimationFrame(tween)
  }
  tween()
}

function resetView() {
  const duration = 2000
  const startPos = camera.position.clone()
  const endPos = new THREE.Vector3(0, 150, 400)
  const startTime = Date.now()
  
  function tween() {
    const elapsed = Date.now() - startTime
    const t = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - t, 3)
    
    camera.position.lerpVectors(startPos, endPos, eased)
    controls.update()
    
    if (t < 1) requestAnimationFrame(tween)
  }
  tween()
}

function addStreamLine(text) {
  const container = document.getElementById('data-stream')
  if (!container) return

  const line = document.createElement('div')
  line.style.cssText = 'animation: fadeIn 0.3s ease; padding: 2px 0; border-bottom: 1px solid rgba(0,242,255,0.1);'
  line.textContent = `[${new Date().toLocaleTimeString('th-TH')}] ${text}`
  container.insertBefore(line, container.firstChild)

  // Keep only last 15 lines
  while (container.children.length > 15) {
    container.removeChild(container.lastChild)
  }
}

function showResponse(data) {
  const display = document.getElementById('response-display')
  const content = document.getElementById('response-content')
  if (!display || !content) return

  content.innerHTML = `
    <div style="font-family: 'Orbitron'; color: var(--primary); margin-bottom: 15px; font-size: 12px;">
      NEURAL RESPONSE
    </div>
    <div>${JSON.stringify(data, null, 2)}</div>
  `
  display.classList.add('active')

  display.onclick = () => display.classList.remove('active')
}

// Initialize
window.addEventListener('load', () => {
  if (typeof THREE !== 'undefined') {
    initNeuralNetwork()
    addStreamLine('Neural network initialized')
    addStreamLine('Core system online')
    addStreamLine('Connections established')
  } else {
    console.error('Three.js not loaded')
  }
})

// Expose to window
window.zoomToCore = zoomToCore
window.resetView = resetView
window.addStreamLine = addStreamLine
window.showResponse = showResponse
