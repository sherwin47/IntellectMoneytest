// frontend/js/auth.js
document.addEventListener('DOMContentLoaded', () => {
    
    const logoutButtons = document.querySelectorAll('.logout-button');

    logoutButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            
            localStorage.removeItem('userToken');
            
            window.location.href = 'index.html';
        });
    });
});