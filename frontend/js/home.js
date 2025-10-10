// frontend/js/home.js

document.addEventListener('DOMContentLoaded', () => {
    
    async function loadMarketNews() {
        const newsList = document.getElementById('news-list');
        try {
            const response = await fetch('https://intellect-money-backend.onrender.com/api/recommendations');
            if (!response.ok) throw new Error('Failed to load news.');
            
            const data = await response.json();

            if (data.articles && data.articles.length > 0) {
                newsList.innerHTML = data.articles.map(article => `
                    <li>
                        <a href="${article.url}" target="_blank" rel="noopener noreferrer">${article.title}</a>
                        <p>${article.summary}</p>
                        <span class="news-source">Source: ${article.source}</span>
                    </li>
                `).join('');
            } else {
                newsList.innerHTML = '<li>No recent news found.</li>';
            }
        } catch (error) {
            console.error('Error fetching news:', error);
            newsList.innerHTML = '<li>Could not load news at this time.</li>';
        }
    }
    
    // Call the function to load news when the page loads
    loadMarketNews();
});