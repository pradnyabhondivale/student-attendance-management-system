document.addEventListener('DOMContentLoaded', function() {
    
    // Count-up animation for dashboard stats cards
    const counters = document.querySelectorAll('.count-up');
    const speed = 150; // A lower number means a faster animation

    counters.forEach(counter => {
        const animate = () => {
            const target = +counter.getAttribute('data-target');
            const count = +counter.innerText;
            const increment = Math.ceil(target / speed);

            if (count < target) {
                counter.innerText = Math.min(count + increment, target);
                setTimeout(animate, 10);
            } else {
                counter.innerText = target;
            }
        };
        // Run the animation
        animate();
    });
});