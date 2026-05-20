(function(){
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (typeof tsParticles === 'undefined') return;
    tsParticles.load('particles-container', {
        fullScreen: { enable: false },
        particles: {
            number: { value: 80 },
            shape: { type: 'circle' },
            size: { value: { min: 1, max: 3 } },
            move: { enable: true, speed: 1 }
        }
    });
})();
