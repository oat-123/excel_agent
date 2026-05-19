// J.A.R.V.I.S NEURAL INTERFACE v5.2 - Unique HUD Logic
(function() {
    let progress = 0;
    let loadingInterval;
    let uptimeSeconds = 0;

    const updateProgress = (target, speed = 20) => {
        if (loadingInterval) clearInterval(loadingInterval);
        loadingInterval = setInterval(() => {
            const progressBar = document.getElementById('progress-bar');
            const progressText = document.getElementById('progress-text');
            if (progress < target) {
                progress += 1;
                if (progressBar) progressBar.style.width = `${progress}%`;
                if (progressText) progressText.innerText = `NEURAL SYNC IN PROGRESS: ${progress}%`;
            } else {
                clearInterval(loadingInterval);
                if (progress >= 100) {
                    setTimeout(() => {
                        const loader = document.getElementById('loading-screen');
                        if (loader) {
                            loader.style.opacity = '0';
                            setTimeout(() => loader.remove(), 1000);
                        }
                    }, 500);
                }
            }
        }, speed);
    };

    updateProgress(40, 30);
    setTimeout(() => updateProgress(80, 50), 1500);
    setTimeout(() => updateProgress(100, 10), 3000);

    let scene, camera, renderer, composer, controls, core;
    let brainGroup, dataPulses = [];
    const NODE_COUNT = 500;
    const MAX_DISTANCE = 110;
    const PULSE_COUNT = 50;

    let processingParticles = [];
    let isProcessing = false;
    let baseRotationSpeed = 0.001;

    window.startProcessing = () => {
        isProcessing = true;
        baseRotationSpeed = 0.03; // spin faster
        if (core) {
            gsap.to(core.scale, { x: 2.5, y: 2.5, z: 2.5, duration: 0.5 });
            gsap.to(core.material, { opacity: 0.8, duration: 0.5 });
            core.material.color.setHex(0xffcc00); // Yellow processing
        }
    };

    window.stopProcessing = () => {
        isProcessing = false;
        baseRotationSpeed = 0.001;
        if (core) {
            gsap.to(core.scale, { x: 1, y: 1, z: 1, duration: 1 });
            gsap.to(core.material, { opacity: 0.1, duration: 1 });
            core.material.color.setHex(0x00f2ff); // Cyan normal
        }
    };

    function init() {
        const container = document.getElementById('canvas-container');
        if (!container) return;

        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 5000);
        camera.position.set(0, 200, 800);

        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.setSize(window.innerWidth, window.innerHeight);
        container.appendChild(renderer.domElement);

        controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.minDistance = 200;
        controls.maxDistance = 1500;

        brainGroup = new THREE.Group();
        scene.add(brainGroup);

        const coreGeom = new THREE.SphereGeometry(60, 32, 32);
        const coreMat = new THREE.MeshBasicMaterial({ color: 0x00f2ff, transparent: true, opacity: 0.1, wireframe: true });
        core = new THREE.Mesh(coreGeom, coreMat);
        brainGroup.add(core);

        const nodes = [];
        const positions = new Float32Array(NODE_COUNT * 3);
        for (let i = 0; i < NODE_COUNT; i++) {
            const side = Math.random() > 0.5 ? 1 : -1;
            const r = 200 + Math.random() * 50;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.random() * Math.PI;
            let x = (r * Math.sin(phi) * Math.cos(theta) * 1.4 + Math.sin(phi * 10) * 20) * side;
            let y = r * Math.sin(phi) * Math.sin(theta);
            let z = r * Math.cos(phi) * 1.1;
            positions[i*3] = x; positions[i*3+1] = y; positions[i*3+2] = z;
            nodes.push(new THREE.Vector3(x, y, z));
        }
        const particlesGeom = new THREE.BufferGeometry();
        particlesGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const pMat = new THREE.PointsMaterial({ color: 0x00f2ff, size: 2, transparent: true, opacity: 0.8 });
        const points = new THREE.Points(particlesGeom, pMat);
        brainGroup.add(points);

        const connections = [];
        const linePos = [];
        const lineCol = [];
        for (let i = 0; i < NODE_COUNT; i++) {
            for (let j = i + 1; j < NODE_COUNT; j++) {
                const dist = nodes[i].distanceTo(nodes[j]);
                if (dist < MAX_DISTANCE) {
                    connections.push({ from: nodes[i], to: nodes[j] });
                    linePos.push(nodes[i].x, nodes[i].y, nodes[i].z, nodes[j].x, nodes[j].y, nodes[j].z);
                    const a = (1 - dist/MAX_DISTANCE) * 0.3;
                    lineCol.push(0, a*0.8, a, 0, a*0.8, a);
                }
            }
        }
        const lineGeom = new THREE.BufferGeometry();
        lineGeom.setAttribute('position', new THREE.Float32BufferAttribute(linePos, 3));
        lineGeom.setAttribute('color', new THREE.Float32BufferAttribute(lineCol, 3));
        const lineMesh = new THREE.LineSegments(lineGeom, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, blending: THREE.AdditiveBlending }));
        brainGroup.add(lineMesh);

        // 1. Confidence Field (Glowing Aura)
        const auraGeo = new THREE.SphereGeometry(100, 32, 32);
        const auraMat = new THREE.MeshPhongMaterial({ 
            color: 0x00f2ff, 
            transparent: true, 
            opacity: 0.05, 
            side: THREE.BackSide,
            blending: THREE.AdditiveBlending 
        });
        window.confidenceAura = new THREE.Mesh(auraGeo, auraMat);
        brainGroup.add(window.confidenceAura);

        // 2. Alert Ripple System
        const rippleGeo = new THREE.RingGeometry(1, 2, 64);
        const rippleMat = new THREE.MeshBasicMaterial({ color: 0xff0000, transparent: true, side: THREE.DoubleSide });
        window.ripples = [];
        window.triggerRipple = (color = 0xff0000) => {
            const ripple = new THREE.Mesh(rippleGeo, rippleMat.clone());
            ripple.material.color.setHex(color);
            ripple.rotation.x = Math.PI / 2;
            scene.add(ripple);
            window.ripples.push(ripple);
            gsap.to(ripple.scale, { x: 500, y: 500, duration: 2, ease: "power1.out" });
            gsap.to(ripple.material, { opacity: 0, duration: 2, onComplete: () => {
                scene.remove(ripple);
                window.ripples = window.ripples.filter(r => r !== ripple);
            }});
        };

        // 3. Connection Lines with Usage Weighting
        window.moduleConnections = {};
        const createModuleConnection = (moduleKey, targetPos) => {
            const geom = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,0,0), targetPos]);
            const mat = new THREE.LineBasicMaterial({ color: 0x00f2ff, transparent: true, opacity: 0.2 });
            const line = new THREE.Line(geom, mat);
            brainGroup.add(line);
            return line;
        };

        setTimeout(() => {
            window.moduleConnections.DB = createModuleConnection('DB', window.modules.DB.position);
            window.moduleConnections.EXCEL = createModuleConnection('EXCEL', window.modules.EXCEL.position);
            window.moduleConnections.LLM = createModuleConnection('LLM', window.modules.LLM.position);
        }, 1500);

        window.updateNeuralConfidence = (level) => {
            const color = level > 0.8 ? 0x00f2ff : (level > 0.5 ? 0xffff00 : 0xffaa00);
            gsap.to(window.confidenceAura.material.color, { r: ((color >> 16) & 255) / 255, g: ((color >> 8) & 255) / 255, b: (color & 255) / 255, duration: 1 });
            gsap.to(window.confidenceAura.scale, { x: 0.8 + level*0.4, y: 0.8 + level*0.4, z: 0.8 + level*0.4, duration: 1 });
        };

        if (connections.length > 0) {
            const pulseGeom = new THREE.SphereGeometry(1.5, 8, 8);
            const pulseMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0 });
            for (let i = 0; i < PULSE_COUNT; i++) {
                const pulse = new THREE.Mesh(pulseGeom, pulseMat.clone());
                dataPulses.push({ 
                    mesh: pulse, 
                    conn: connections[Math.floor(Math.random() * connections.length)], 
                    t: Math.random(),
                    speed: 0.005 + Math.random() * 0.01 
                });
                brainGroup.add(pulse);
            }
        }

        composer = new THREE.EffectComposer(renderer);
        composer.addPass(new THREE.RenderPass(scene, camera));
        composer.addPass(new THREE.UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 2.5, 0.4, 0.1));

        // Functional Modules for Data Flow visualization
        window.modules = {};
        const createModule = (name, color, pos) => {
            const group = new THREE.Group();
            const geometry = new THREE.CylinderGeometry(15, 15, 5, 6);
            const material = new THREE.MeshPhongMaterial({ color, emissive: color, emissiveIntensity: 0.5, transparent: true, opacity: 0.6, wireframe: true });
            const mesh = new THREE.Mesh(geometry, material);
            mesh.rotation.x = Math.PI / 2;
            group.add(mesh);
            const coreGeo = new THREE.SphereGeometry(6, 16, 16);
            const coreMat = new THREE.MeshBasicMaterial({ color });
            group.add(new THREE.Mesh(coreGeo, coreMat));
            
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = 256; canvas.height = 64;
            ctx.fillStyle = '#00f2ff'; ctx.font = 'bold 32px Orbitron'; ctx.textAlign = 'center';
            ctx.fillText(name, 128, 40);
            const texture = new THREE.CanvasTexture(canvas);
            const label = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true }));
            label.position.y = 25; label.scale.set(40, 10, 1);
            group.add(label);
            group.position.copy(pos);
            scene.add(group);
            return group;
        };

        window.modules.CORE = createModule('CORE', 0x00f2ff, new THREE.Vector3(0, 0, -150));
        window.modules.DB = createModule('DATABASE', 0xff00ff, new THREE.Vector3(-250, 100, -250));
        window.modules.EXCEL = createModule('EXCEL', 0x00ff00, new THREE.Vector3(250, 100, -250));
        window.modules.LLM = createModule('LLM', 0xffff00, new THREE.Vector3(0, 250, -300));

        window.animateDataFlow = (moduleKey) => {
            const target = window.modules[moduleKey];
            if (!target) return;
            const packet = new THREE.Mesh(new THREE.SphereGeometry(4, 8, 8), new THREE.MeshBasicMaterial({ color: 0x00f2ff }));
            packet.position.set(0, -200, 200); // Start from input area
            scene.add(packet);
            gsap.to(packet.position, { x: target.position.x, y: target.position.y, z: target.position.z, duration: 1.2, ease: "power2.inOut", onComplete: () => {
                gsap.to(target.scale, { x: 1.5, y: 1.5, z: 1.5, duration: 0.2, yoyo: true, repeat: 1 });
                scene.remove(packet);
            }});
        };

        // 4. Decision Path Visualization
        window.activePathLines = [];
        window.visualizeDecisionPath = (steps) => {
            // Clear old paths
            window.activePathLines.forEach(line => scene.remove(line));
            window.activePathLines = [];
            
            const startPoint = new THREE.Vector3(0, -200, 200); // Input Area
            const endPoint = new THREE.Vector3(-400, 50, 100);  // Hologram Area
            const corePoint = new THREE.Vector3(0, 0, 0);       // Brain Core
            
            const points = [startPoint];
            
            // Helper to get a curved midpoint to avoid piercing core
            const getCurvedPoint = (p1, p2, offset = 150) => {
                const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
                mid.normalize().multiplyScalar(300 + offset); // Push outside brain radius
                return mid;
            };

            steps.forEach(step => {
                let moduleNode = null;
                if (step.includes('ฐานข้อมูล') || step.includes('DB')) moduleNode = window.modules.DB;
                else if (step.includes('ไฟล์') || step.includes('Excel')) moduleNode = window.modules.EXCEL;
                else if (step.includes('LLM') || step.includes('ประมวลผล')) moduleNode = window.modules.LLM;
                
                if (moduleNode) {
                    const targetPos = moduleNode.position.clone();
                    // Curve from last point to module
                    points.push(getCurvedPoint(points[points.length-1], targetPos));
                    points.push(targetPos);
                }
            });
            
            // From last module to Core
            points.push(getCurvedPoint(points[points.length-1], corePoint));
            points.push(corePoint);
            // From Core to Output
            points.push(getCurvedPoint(corePoint, endPoint));
            points.push(endPoint);
            
            // ==== NEW FEATURES: Neural Rest Mode & Adaptive Cognitive Load ====
            window.lastCommandTime = Date.now();
            window.idleTimeout = null;
            window.restModeActive = false;
            window.commandTimestamps = [];

            window.resetIdleTimer = function() {
                window.lastCommandTime = Date.now();
                if (window.idleTimeout) clearTimeout(window.idleTimeout);
                window.idleTimeout = setTimeout(window.enterRestMode, 120000);
                if (window.restModeActive) window.exitRestMode();
            };

            window.enterRestMode = function() {
                window.restModeActive = true;
                if (window.pulse) window.pulse.scale.set(0.7, 0.7, 0.7);
                scene.traverse(obj => {
                    if (obj.isMesh && obj.material && obj.material.color) {
                        if (!obj.userData.originalColor) obj.userData.originalColor = obj.material.color.getHex();
                        obj.material.color.set(0x2a004d);
                    }
                });
                const desc = document.getElementById('objective-desc');
                if (desc) gsap.fromTo(desc, { opacity: 0 }, { opacity: 1, duration: 0.8 });
                window.updateObjective('REST_MODE', 'Neural Rest Mode engaged - consolidating memories.');
            };

            window.exitRestMode = function() {
                window.restModeActive = false;
                if (window.pulse) window.pulse.scale.set(1, 1, 1);
                scene.traverse(obj => {
                    if (obj.isMesh && obj.material && obj.userData && obj.userData.originalColor) {
                        obj.material.color.set(obj.userData.originalColor);
                    }
                });
                const desc = document.getElementById('objective-desc');
                if (desc) gsap.fromTo(desc, { opacity: 0 }, { opacity: 1, duration: 0.8 });
                window.updateObjective('AWAITING_INPUT', 'System ready. Standing by for user commands, excel processing, or data queries.');
            };

            window.recordCommand = function() {
                const now = Date.now();
                window.commandTimestamps.push(now);
                window.commandTimestamps = window.commandTimestamps.filter(t => now - t <= 60000);
                window.updateCognitiveLoadIcon();
            };

            window.updateCognitiveLoadIcon = function() {
                const count = window.commandTimestamps.length;
                const icon = document.getElementById('cog-load-icon');
                if (!icon) return;
                let level = 0;
                if (count >= 8) level = 2;
                else if (count >= 2) level = 1;
                const symbols = ['▢▢▢', '▢▢▣', '▢▣▣'];
                icon.innerText = symbols[level];
            };

            const curve = new THREE.CatmullRomCurve3(points);
            const tubeGeo = new THREE.TubeGeometry(curve, 128, 0.8, 8, false);
            const tubeMat = new THREE.MeshPhongMaterial({ 
                color: 0x00f2ff, 
                emissive: 0x00f2ff,
                emissiveIntensity: 2,
                transparent: true, 
                opacity: 0.5,
                blending: THREE.AdditiveBlending
            });
            const pathMesh = new THREE.Mesh(tubeGeo, tubeMat);
            scene.add(pathMesh);
            window.activePathLines.push(pathMesh);
            
            // Animated pulse along the line
            const pulse = new THREE.Mesh(
                new THREE.SphereGeometry(3, 16, 16),
                new THREE.MeshBasicMaterial({ color: 0xffffff })
            );
            scene.add(pulse);
            window.activePathLines.push(pulse);
            
            gsap.to({}, {
                duration: 2,
                repeat: -1,
                onUpdate: function() {
                    const t = (this.progress());
                    const pos = curve.getPoint(t);
                    pulse.position.copy(pos);
                }
            });

            // Path fade out after a while
            gsap.to(pathMesh.material, { opacity: 0, duration: 1, delay: 10, onComplete: () => scene.remove(pathMesh) });
            gsap.to(pulse.material, { opacity: 0, duration: 1, delay: 10, onComplete: () => scene.remove(pulse) });
        };

        function animate() {
            requestAnimationFrame(animate);
            if (controls) controls.update();
            dataPulses.forEach(p => {
                if (!p.conn) return;
                p.t += p.speed;
                if (p.t >= 1) { 
                    p.t = 0; 
                    if (connections.length > 0) p.conn = connections[Math.floor(Math.random() * connections.length)]; 
                }
                p.mesh.position.lerpVectors(p.conn.from, p.conn.to, p.t);
                p.mesh.material.opacity = Math.sin(p.t * Math.PI) * 0.8;
            });
            if (isProcessing) {
                // Spawn incoming data chunks
                for(let i=0; i<3; i++) {
                    const pGeom = new THREE.SphereGeometry(2, 4, 4);
                    const pMat = new THREE.MeshBasicMaterial({ color: 0xffcc00, transparent: true, opacity: 0.9 });
                    const pMesh = new THREE.Mesh(pGeom, pMat);
                    
                    const r = 600 + Math.random() * 200;
                    const theta = Math.random() * Math.PI * 2;
                    const phi = Math.random() * Math.PI;
                    pMesh.position.set(
                        r * Math.sin(phi) * Math.cos(theta),
                        r * Math.sin(phi) * Math.sin(theta),
                        r * Math.cos(phi)
                    );
                    brainGroup.add(pMesh);
                    processingParticles.push({ mesh: pMesh, life: 1 });
                }
            }

            for (let i = processingParticles.length - 1; i >= 0; i--) {
                const p = processingParticles[i];
                p.mesh.position.lerp(new THREE.Vector3(0,0,0), 0.1); // Move to core
                p.life -= 0.02;
                p.mesh.scale.setScalar(p.life);
                if (p.mesh.position.length() < 30 || p.life <= 0) {
                    brainGroup.remove(p.mesh);
                    processingParticles.splice(i, 1);
                }
            }

            if (brainGroup) brainGroup.rotation.y += baseRotationSpeed;
            if (composer) composer.render();
        }
        animate();
    }

    window.injectSignal = () => {
        if (!core) return;
        gsap.to(core.scale, { x: 1.5, y: 1.5, z: 1.5, duration: 0.3, yoyo: true, repeat: 1 });
        gsap.to(core.material, { opacity: 0.8, duration: 0.3, yoyo: true, repeat: 1 });
        dataPulses.forEach(p => { p.speed *= 2; });
        setTimeout(() => { dataPulses.forEach(p => { p.speed /= 2; }); }, 2000);
    };

    window.emitResponse = () => {
        if (!brainGroup) return;
        const ringGeom = new THREE.RingGeometry(1, 2, 32);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0x00f2ff, transparent: true, side: THREE.DoubleSide });
        const ring = new THREE.Mesh(ringGeom, ringMat);
        ring.rotation.x = Math.PI / 2;
        brainGroup.add(ring);
        gsap.to(ring.scale, { x: 500, y: 500, duration: 1, ease: "power2.out" });
        gsap.to(ring.material, { opacity: 0, duration: 1, onComplete: () => brainGroup.remove(ring) });
    };

    // HUD Polling & Timer
    setInterval(() => {
        uptimeSeconds++;
        const h = Math.floor(uptimeSeconds / 3600).toString().padStart(2, '0');
        const m = Math.floor((uptimeSeconds % 3600) / 60).toString().padStart(2, '0');
        const s = (uptimeSeconds % 60).toString().padStart(2, '0');
        const uptimeEl = document.getElementById('neural-uptime-val');
        if (uptimeEl) uptimeEl.innerText = `${h}:${m}:${s}`;

        const activityEl = document.getElementById('neural-activity-val');
        if (activityEl) {
            const val = 70 + Math.floor(Math.random() * 25);
            activityEl.innerText = `${val}%`;
        }
        const synapseEl = document.getElementById('neural-synapse-count');
        if (synapseEl) synapseEl.innerText = (3000 + Math.floor(Math.random() * 200)).toLocaleString();
    }, 1000);

    setInterval(async () => {
        try {
            const res = await fetch('/system_stats');
            const data = await res.json();
            if (document.getElementById('cpu-val')) document.getElementById('cpu-val').innerText = data.cpu_usage;
            if (document.getElementById('temp-val')) document.getElementById('temp-val').innerText = data.cpu_temp;
            if (document.getElementById('ram-val')) document.getElementById('ram-val').innerText = data.ram_usage;
            if (document.getElementById('disk-val')) document.getElementById('disk-val').innerText = data.disk_free;
            if (document.getElementById('repo-val')) document.getElementById('repo-val').innerText = data.project_size;
        } catch (e) {}
    }, 3000);

    const SUGGESTIONS = ["หาข้อมูล ", "ดูข้อมูล ", "โหลด db", "หาเบอร์ ", "ค้นหาไฟล์ ", "ช่วยหา ", "sync db"];
    let suggestionNodes = [];

    window.update3DSuggestions = (input) => {
        // Clear old suggestions
        suggestionNodes.forEach(s => scene.remove(s));
        suggestionNodes = [];
        
        if (!input.trim()) return;
        
        const filtered = SUGGESTIONS.filter(s => s.includes(input.toLowerCase()) && s !== input.toLowerCase());
        
        filtered.forEach((text, i) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = 512; canvas.height = 128;
            
            // Neon bubble background
            ctx.fillStyle = 'rgba(0, 242, 255, 0.1)';
            ctx.roundRect(0, 0, 512, 128, 64);
            ctx.fill();
            ctx.strokeStyle = '#00f2ff';
            ctx.lineWidth = 4;
            ctx.stroke();
            
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 48px Orbitron';
            ctx.textAlign = 'center';
            ctx.fillText(text, 256, 80);
            
            const texture = new THREE.CanvasTexture(canvas);
            const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
            const sprite = new THREE.Sprite(material);
            
            // Position in semi-circle around input area
            const angle = (i / (filtered.length - 1 || 1)) * Math.PI - Math.PI;
            sprite.position.set(Math.cos(angle) * 150, -120 + Math.sin(angle) * 50, 150);
            sprite.scale.set(80, 20, 1);
            
            sprite.userData = { text: text };
            scene.add(sprite);
            suggestionNodes.push(sprite);
            
            // Gentle float animation
            gsap.to(sprite.position, { y: sprite.position.y + 10, duration: 1 + Math.random(), yoyo: true, repeat: -1, ease: "sine.inOut" });
        });
    };

    // Click to select suggestion
    window.addEventListener('click', (event) => {
        const mouse = new THREE.Vector2(
            (event.clientX / window.innerWidth) * 2 - 1,
            -(event.clientY / window.innerHeight) * 2 + 1
        );
        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(suggestionNodes);
        
        if (intersects.length > 0) {
            const text = intersects[0].object.userData.text;
            const input = document.getElementById('neural-cmd');
            if (input) {
                input.value = text;
                input.focus();
                window.update3DSuggestions(text);
            }
        }
    });

    window.addStreamLine = (text, type = 'info', save = true) => {
        const container = document.getElementById('data-stream');
        if (!container) return;
        const line = document.createElement('div');
        let color = 'rgba(0, 242, 255, 0.7)';
        let prefix = `[${new Date().toLocaleTimeString()}] `;
        if (type === 'bot') {
            color = '#ffcc00'; prefix = 'J.A.R.V.I.S >> '; line.style.fontWeight = 'bold';
        } else if (type === 'error') color = '#ff4d4d';
        line.style.cssText += `padding: 4px 0; border-bottom: 1px solid rgba(0,242,255,0.05); font-size: 11px; color: ${color};`;
        line.textContent = `${prefix}${text}`;
        container.prepend(line);
        if (container.children.length > 30) container.removeChild(container.lastChild);
        if (save) {
            const logs = JSON.parse(localStorage.getItem('jarvis_neural_logs') || '[]');
            logs.unshift({ text, type, time: new Date().toLocaleTimeString() });
            localStorage.setItem('jarvis_neural_logs', JSON.stringify(logs.slice(0, 30)));
        }
    };

    window.clearNeuralLogs = () => {
        localStorage.removeItem('jarvis_neural_logs');
        const container = document.getElementById('data-stream');
        if (container) container.innerHTML = '';
        window.addStreamLine("Neural logs cleared.", "info", true);
    };

    const loadPersistentLogs = () => {
        const logs = JSON.parse(localStorage.getItem('jarvis_neural_logs') || '[]');
        logs.reverse().forEach(log => { window.addStreamLine(log.text, log.type, false); });
    };

    window.showResponse = (data, processTime) => {
        window.addStreamLine(data.message || data.response || "Task complete.", 'bot');
        
        // Trigger Neural Visuals
        if (data.confidence !== undefined && window.updateNeuralConfidence) {
            window.updateNeuralConfidence(data.confidence);
        }
        if (data.alert && window.triggerRipple) {
            window.triggerRipple(0xff0000); // Red ripple for anomaly
            window.addStreamLine("PROACTIVE ALERT: Neural link detected data anomaly.", "error");
        } else if (data.status === 'success' && window.triggerRipple) {
            window.triggerRipple(0x00f2ff); // Cyan ripple for success
        }

        // Visualize Decision Path
        if (data.steps && window.visualizeDecisionPath) {
            window.visualizeDecisionPath(data.steps);
        }

        if (data.rows && data.rows.length > 0) {
            window.showHologram(data.rows, processTime);
        } else {
            const toastContainer = document.getElementById('neural-toast-container');
            if (toastContainer) {
                const toast = document.createElement('div');
                toast.style.cssText = `background: rgba(10, 15, 26, 0.95); border-left: 4px solid #ffcc00; padding: 12px 20px; color: #fff; font-size: 12px; font-family: 'Inter', sans-serif; backdrop-filter: blur(15px); border-radius: 4px; box-shadow: 0 5px 25px rgba(0,0,0,0.6); min-width: 250px; opacity: 0; transform: translateX(20px); transition: 0.4s;`;
                toast.innerHTML = `<strong style="color:#ffcc00; display:block; margin-bottom:4px; font-family:Orbitron; font-size:10px;">INCOMING DATA</strong>${data.message || data.response}`;
                toastContainer.appendChild(toast);
                setTimeout(() => { toast.style.opacity = '1'; toast.style.transform = 'translateX(0)'; }, 10);
                setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateX(20px)'; setTimeout(() => toast.remove(), 400); }, 6000);
            }
        }
        window.emitResponse();
    };

    window.closeHologram = () => {
        const modal = document.getElementById('hologram-modal');
        if (modal) {
            modal.classList.remove('active');
            if (brainGroup) gsap.to(brainGroup.position, { x: 0, duration: 1, ease: "power2.out" });
        }
    };

    const typeWriter = (element, text, speed = 30) => {
        element.innerHTML = '';
        let i = 0;
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*';
        let garbledInterval = setInterval(() => {
            let garbled = '';
            for(let j = i; j < text.length; j++) { garbled += chars[Math.floor(Math.random() * chars.length)]; }
            element.innerHTML = text.substring(0, i) + `<span style="opacity:0.5">${garbled}</span>`;
        }, 50);

        const typing = setInterval(() => {
            i++;
            if (i > text.length) {
                clearInterval(typing);
                clearInterval(garbledInterval);
                element.innerHTML = text;
            }
        }, speed);
    };

    let lastProcessTime = 0;
    let hologramRows = [];
    let currentHologramIndex = 0;

    window.nextHologram = () => {
        if (hologramRows.length <= 1) return;
        currentHologramIndex = (currentHologramIndex + 1) % hologramRows.length;
        window.updateHologramView(hologramRows[currentHologramIndex], currentHologramIndex, hologramRows.length, lastProcessTime);
    };

    window.prevHologram = () => {
        if (hologramRows.length <= 1) return;
        currentHologramIndex = (currentHologramIndex - 1 + hologramRows.length) % hologramRows.length;
        window.updateHologramView(hologramRows[currentHologramIndex], currentHologramIndex, hologramRows.length, lastProcessTime);
    };

    // ── Selected rows store (shared across hologram cards) ──────────────
    if (!window.hologramSelectedRows) window.hologramSelectedRows = new Set();

    window.toggleHologramSelect = (rowId, btn) => {
        if (window.hologramSelectedRows.has(rowId)) {
            window.hologramSelectedRows.delete(rowId);
            btn.classList.remove('holo-check-active');
            btn.title = 'เลือกรายชื่อนี้';
        } else {
            window.hologramSelectedRows.add(rowId);
            btn.classList.add('holo-check-active');
            btn.title = 'ยกเลิกการเลือก';
        }
    };

    window.showHologram = (rows, processTime) => {
        hologramRows = rows;
        currentHologramIndex = 0;
        lastProcessTime = processTime || 0;
        
        const modal = document.getElementById('hologram-modal');
        if (!modal) return;
        
        if (brainGroup) {
            gsap.to(brainGroup.position, { x: -300, duration: 1, ease: "power2.out" });
        }
        
        modal.classList.add('active');
        window.updateHologramView(rows[0], 0, rows.length, lastProcessTime);
    };

    window.updateHologramView = (target, index, total, processTime) => {
        const timeElem = document.getElementById('process-time');
        if (timeElem && processTime !== undefined) {
            timeElem.innerText = `PROC: ${processTime}ms`;
        }
        
        const modal = document.getElementById('hologram-modal');
        const card = modal.querySelector('.hologram-card');
        card.classList.remove('glitching');
        void card.offsetWidth;
        card.classList.add('glitching');
        
        const idElem = document.getElementById('target-id');
        if (idElem) typeWriter(idElem, `ID: ${target['ลำดับ'] || 'UNKNOWN'} | CLASS: ${target['ชั้นปีที่'] || 'N/A'}`);
        
        const counter = document.getElementById('hologram-counter');
        const nav = document.getElementById('hologram-nav');
        if (total > 1) {
            if (counter) {
                counter.innerText = `${index + 1} / ${total}`;
                counter.style.display = 'block';
            }
            if (nav) nav.style.display = 'flex';
        } else {
            if (counter) counter.style.display = 'none';
            if (nav) nav.style.display = 'none';
        }
        
        const detailsContainer = document.getElementById('target-details');
        detailsContainer.innerHTML = '';
        
        const keysToSkip = ['ลำดับ', 'ชั้นปีที่'];
        let delay = 0;
        
        const nameStr = `${target['ยศ'] || ''} ${target['ชื่อ'] || ''} ${target['สกุล'] || ''}`.trim();
        if (nameStr) {
            const rowDiv = document.createElement('div');
            rowDiv.className = 'data-row';
            const nameId = `val-name-${Date.now()}`;
            rowDiv.innerHTML = `<div class="data-label">PROFILE NAME</div><div class="data-value" id="${nameId}"></div>`;
            detailsContainer.appendChild(rowDiv);
            setTimeout(() => {
                const el = document.getElementById(nameId);
                if (el) typeWriter(el, nameStr, 20);
            }, delay);
            delay += 200;
        }

        Object.keys(target).forEach(key => {
            if (keysToSkip.includes(key) || ['ยศ', 'ชื่อ', 'สกุล'].includes(key) || !target[key]) return;
            const rowDiv = document.createElement('div');
            rowDiv.className = 'data-row';
            const valId = `val-${Math.random().toString(36).substr(2, 5)}`;
            rowDiv.innerHTML = `<div class="data-label">${key.toUpperCase()}</div><div class="data-value" id="${valId}"></div>`;
            detailsContainer.appendChild(rowDiv);
            
            setTimeout(() => {
                const el = document.getElementById(valId);
                if (el) typeWriter(el, String(target[key]), 20);
            }, delay);
            delay += 150;
        });
        
        const fill = modal.querySelector('.status-fill');
        if (fill) {
            fill.style.animation = 'none';
            void fill.offsetWidth;
            fill.style.animation = 'fillBar 1.5s forwards ease-out';
        }

        // ── Checkmark select button (bottom-right of card) ───────────────
        const rowId = String(target['ลำดับ'] || target['ชื่อ'] || index);
        let checkBtn = modal.querySelector('.holo-select-btn');
        if (!checkBtn) {
            checkBtn = document.createElement('button');
            checkBtn.className = 'holo-select-btn';
            checkBtn.title = 'เลือกรายชื่อนี้';
            checkBtn.innerHTML = '✓';
            modal.querySelector('.hologram-card').appendChild(checkBtn);
        }
        // Update state for current card
        checkBtn.dataset.rowId = rowId;
        if (window.hologramSelectedRows && window.hologramSelectedRows.has(rowId)) {
            checkBtn.classList.add('holo-check-active');
            checkBtn.title = 'ยกเลิกการเลือก';
        } else {
            checkBtn.classList.remove('holo-check-active');
            checkBtn.title = 'เลือกรายชื่อนี้';
        }
        checkBtn.onclick = () => window.toggleHologramSelect(checkBtn.dataset.rowId, checkBtn);
    };

    window.updateObjective = (tag, desc) => {
        const tagElem = document.getElementById('objective-tag');
        const descElem = document.getElementById('objective-desc');
        if (tagElem) tagElem.innerText = `> ${tag.toUpperCase()}`;
        if (descElem) {
            gsap.fromTo(descElem, { opacity: 0 }, { opacity: 1, duration: 0.5 });
            descElem.innerText = desc;
        }
    };

    let lastObjectiveSignature = '';
    const syncObjectiveState = async () => {
        try {
            const res = await fetch('/brain/objective');
            if (!res.ok) return;
            const state = await res.json();
            const tag = state.tag || 'AWAITING_INPUT';
            const desc = state.desc || 'Neural status unavailable.';
            const signature = `${tag}::${desc}`;
            if (signature !== lastObjectiveSignature) {
                lastObjectiveSignature = signature;
                window.updateObjective(tag, desc);
            }
        } catch (e) {
            // Keep silent; UI should not flicker on temporary backend/network hiccups.
        }
    };

    window.sendNeuralCommand = async () => {
        const input = document.getElementById('neural-input');
        const cmd = input.value.trim();
        if (!cmd) return;
        
        input.value = '';
        window.addStreamLine(cmd, 'user');
        window.updateObjective('PROCESSING_QUERY', `Analyzing and executing neural command: "${cmd}"`);
        
        const startTime = Date.now();
        try {
            const response = await fetch('/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd })
            });
            const data = await response.json();
            const processTime = Date.now() - startTime;
            window.showResponse(data, processTime);
            
            if (data.status === 'success') {
                window.updateObjective('MISSION_COMPLETE', data.message || 'Data successfully processed.');
                setTimeout(() => window.updateObjective('AWAITING_INPUT', 'Neural link stable. Standing by for next command.'), 5000);
            } else {
                window.updateObjective('LINK_ERROR', data.message || 'Processing anomaly detected.');
            }
        } catch (err) {
            window.addStreamLine(`Connection Error: ${err.message}`, 'error');
            window.updateObjective('CRITICAL_FAILURE', 'Neural link severed. Re-syncing required.');
        }
    };

    window.addEventListener('load', () => {
        init();
        loadPersistentLogs();
        syncObjectiveState();
    });
    setInterval(syncObjectiveState, 1000);
    
    // Handle responsive panel visibility
    let panelsVisible = true;
    window.addEventListener('resize', () => {
        const toggle = document.getElementById('mobile-panel-toggle');
        if (window.innerWidth <= 768) {
            if (toggle) toggle.style.display = 'block';
        } else {
            if (toggle) toggle.style.display = 'none';
            // Reset panels visibility on desktop
            document.querySelectorAll('.hud-panel').forEach(p => p.style.display = 'block');
            panelsVisible = true;
        }
        
        if (camera && renderer && composer) {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
            composer.setSize(window.innerWidth, window.innerHeight);
        }
    });
    
    // Mobile panel toggle function
    window.togglePanels = () => {
        panelsVisible = !panelsVisible;
        document.querySelectorAll('.hud-panel').forEach(p => {
            p.style.display = panelsVisible ? 'block' : 'none';
        });
        const toggle = document.getElementById('mobile-panel-toggle');
        if (toggle) {
            toggle.innerHTML = panelsVisible ? '<i class="fas fa-times"></i> HIDE' : '<i class="fas fa-bars"></i> SHOW';
        }
    };
})();
