// frontend/js/register.js

document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('register-form');

    registerForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent default form submission

        const fullname = document.getElementById('fullname').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const button = event.target.querySelector('button');

        // 1. Check for empty fields
        if (!fullname || !email || !password) {
            alert('Please fill in all fields.');
            return;
        }

        // 2. NEW: Check for password length (bcrypt limitation)
        if (password.length > 72) {
            alert('Password cannot be longer than 72 characters.');
            return;
        }
        
        button.textContent = 'Creating Account...';
        button.disabled = true;

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ fullname, email, password }),
            });

            if (response.ok) {
                // SUCCESS: Redirect to the login page
                alert('Registration successful! Please log in.');
                window.location.href = 'login.html';
            } else {
                // ERROR: Show an error message
                const errorData = await response.json();
                alert(`Registration failed: ${errorData.detail}`);
            }
        } catch (error) {
            console.error('An error occurred:', error);
            alert('An error occurred during registration. Please try again.');
        } finally {
            button.textContent = 'Create Account';
            button.disabled = false;
        }
    });
});