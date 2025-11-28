

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');

    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault(); 

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const button = event.target.querySelector('button');
        
        
        if (!email || !password) {
            alert('Please fill in all fields.');
            return;
        }

        button.textContent = 'Logging in...';
        button.disabled = true;

        try {
            const response = await fetch('http://127.0.0.1:8000/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password }),
            });

            if (response.ok) {
                
                const data = await response.json();
                
                if (data.access_token) {
                    localStorage.setItem('userToken', data.access_token);
                    window.location.href = 'home.html';
                } else {
                    alert('Login successful, but no token was received.');
                }
                
            } else {
                
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