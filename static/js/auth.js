document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');
    const showSignupBtn = document.getElementById('show-signup');
    const showLoginBtn = document.getElementById('show-login');
    const passwordToggles = document.querySelectorAll('.toggle-password');

    showSignupBtn.addEventListener('click', (e) => {
        e.preventDefault();
        loginForm.classList.remove('active');
        signupForm.classList.add('active');
    });

    showLoginBtn.addEventListener('click', (e) => {
        e.preventDefault();
        signupForm.classList.remove('active');
        loginForm.classList.add('active');
    });

    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const targetInputId = toggle.getAttribute('data-target');
            const passwordInput = document.getElementById(targetInputId);
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                toggle.textContent = 'HIDE';
            } else {
                passwordInput.type = 'password';
                toggle.textContent = 'SHOW';
            }
        });
    });
});