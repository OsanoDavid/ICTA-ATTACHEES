document.addEventListener('DOMContentLoaded', function() {
    console.log("Custom Admin JS Loaded");
    
    // 1. Password Visibility Toggle for Login Page
    const passwordField = document.querySelector('input[type="password"]');
    if (passwordField) {
        const parent = passwordField.parentElement;
        const toggleIcon = parent.querySelector('.fas.fa-lock, .fa-eye-slash');
        
        if (toggleIcon) {
            toggleIcon.style.cursor = 'pointer';
            toggleIcon.className = 'fas fa-eye-slash text-muted'; // Initial state icon
            
            toggleIcon.addEventListener('click', function() {
                if (passwordField.type === 'password') {
                    passwordField.type = 'text';
                    toggleIcon.className = 'fas fa-eye text-primary';
                } else {
                    passwordField.type = 'password';
                    toggleIcon.className = 'fas fa-eye-slash text-muted';
                }
            });
        }
    }

    const versionBlocks = document.querySelectorAll(
        '.app-footer .float-end, .app-footer .float-right, .main-footer .float-end, .main-footer .float-right'
    );
    versionBlocks.forEach(function(block) {
        block.setAttribute('style', 'display: none !important;');
    });

    // 2. Loading Spinner for Login Submit
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function() {
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                // Change button text to have a spinner
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Authenticating...';
            }
        });
    }
});
