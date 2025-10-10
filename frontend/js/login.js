// frontend/js/login.js

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');

    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent the default form submission

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const button = event.target.querySelector('button');
        
        // Basic validation
        if (!email || !password) {
            alert('Please fill in all fields.');
            return;
        }

        button.textContent = 'Logging in...';
        button.disabled = true;

        try {
            const response = await fetch('https://intellect-money-backend.onrender.com/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password }),
            });

            if (response.ok) {
                // SUCCESS: Redirect to the main home page
                alert('Login successful! Redirecting to the homepage.');
                window.location.href = 'home.html'; 
            } else {
                // ERROR: Show an error message
                const errorData = await response.json();
                alert(`Login failed: ${errorData.detail}`);
            }
        } catch (error) {
            console.error('An error occurred:', error);
            alert('An error occurred during login. Please try again.');
        } finally {
            button.textContent = 'Login';
            button.disabled = false;
        }
    });
});