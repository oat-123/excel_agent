(function(){
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (typeof lottie === 'undefined') return;
    lottie.loadAnimation({
        container: document.getElementById('dna-lottie'),
        renderer: 'svg',
        loop: true,
        autoplay: true,
        path: 'https://assets6.lottiefiles.com/packages/lf20_q5pk6p1k.json'
    });
})();
