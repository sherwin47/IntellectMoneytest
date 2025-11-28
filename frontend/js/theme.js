// js/theme.js

document.addEventListener('DOMContentLoaded', () => {
    const toggleButton = document.getElementById('theme-toggle');
    const body = document.body;

    // 1. Check LocalStorage on load
    // If the user previously chose dark, apply it immediately
    if (localStorage.getItem('theme') === 'dark') {
        body.classList.add('dark-mode');
        if(toggleButton) toggleButton.textContent = '☀️ Light Mode';
    }

    // 2. Add Click Event (Only if button exists on this page)
    if (toggleButton) {
        toggleButton.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent link behavior if inside <a>
            body.classList.toggle('dark-mode');

            if (body.classList.contains('dark-mode')) {
                localStorage.setItem('theme', 'dark');
                toggleButton.textContent = '☀️ Light Mode';
            } else {
                localStorage.setItem('theme', 'light');
                toggleButton.textContent = '🌙 Dark Mode';
            }
        });
    }
});