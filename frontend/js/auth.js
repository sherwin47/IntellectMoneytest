// frontend/js/auth.js
document.addEventListener('DOMContentLoaded', () => {
    // Find all logout buttons on the page
    const logoutButtons = document.querySelectorAll('.logout-button');

    logoutButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            // Remove the token from storage
            localStorage.removeItem('userToken');
            // Redirect to the public landing page
            window.location.href = 'index.html';
        });
    });
});