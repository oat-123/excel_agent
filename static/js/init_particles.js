(function(){
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (typeof tsParticles === 'undefined') return;
    tsParticles.load('particles-container', {
        fullScreen: { enable: false },
        particles: {
            number: { value: 40, density: { enable: true, area: 800 } },
            color: { value: '#00f2ff' },
            opacity: { value: 0.06 },
            size: { value: 2 },
            move: { enable: true, speed: 0.6, outModes: 'out' }
        },
        interactivity: {
            events: {
                onhover: { enable: true, mode: 'repulse' }
            }
        }
    }).catch(()=>{});
})();