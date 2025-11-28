

document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('register-form');

    registerForm.addEventListener('submit', async (event) => {
        event.preventDefault(); 

        const fullname = document.getElementById('fullname').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const button = event.target.querySelector('button');

        
        if (!fullname || !email || !password) {
            alert('Please fill in all fields.');
            return;
        }

        
        if (password.length > 72) {
            alert('Password cannot be longer than 72 characters.');
            return;
        }
        
        button.textContent = 'Creating Account...';
        button.disabled = true;

        try {
            const response = await fetch('http://127.0.0.1:8000/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ fullname, email, password }),
            });

            if (response.ok) {
                
                alert('Registration successful! Please log in.');
                window.location.href = 'login.html';
            } else {
                
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