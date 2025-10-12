// frontend/js/dashboard.js

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('userToken');
    const financeForm = document.getElementById('finance-form');
    const recommendationOutput = document.getElementById('recommendation-output');
    
    // --- Elements for the main recommendation display ---
    const savingsPotentialSpan = document.getElementById('savings-potential');
    const investorProfileSpan = document.getElementById('investor-profile');
    const aiSummaryText = document.getElementById('ai-summary-text');
    const recommendationsList = document.getElementById('recommendations-list');
    const chartCanvas = document.getElementById('portfolio-chart');
    
    // --- NEW: Element for the Financial Health Score ---
    const healthScoreDisplay = document.getElementById('health-score-display');
    
    let portfolioChart = null;

    financeForm.addEventListener('submit', async function(event) {
        event.preventDefault();

        const userProfile = {
            income: parseFloat(document.getElementById('monthly-income').value),
            expenses: parseFloat(document.getElementById('monthly-expenses').value),
            savings: parseFloat(document.getElementById('total-savings').value),
            risk_tolerance_input: document.getElementById('risk-tolerance').value
        };

        // --- UI Feedback ---
        recommendationOutput.style.display = 'block';
        healthScoreDisplay.innerHTML = '<p>Calculating your score...</p>'; // Loading state for score
        recommendationsList.innerHTML = '<li>Generating your personalized AI plan...</li>';
        aiSummaryText.textContent = 'Analyzing your profile...';

        try {
            // --- Step 1: Fetch AI Recommendations ---
            const recommendationsResponse = await fetch('http://127.0.0.1:8000/api/recommendations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userProfile),
            });
            if (!recommendationsResponse.ok) {
                const errorData = await recommendationsResponse.json();
                throw new Error(errorData.detail || 'Failed to fetch recommendations');
            }
            const planData = await recommendationsResponse.json();
            displayRecommendations(planData);

            // --- Step 2: Fetch Financial Health Score ---
            const healthScoreResponse = await fetch('http://127.0.0.1:8000/api/health-score', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userProfile),
            });
            if (!healthScoreResponse.ok) {
                throw new Error('Failed to calculate health score.');
            }
            const scoreData = await healthScoreResponse.json();
            displayHealthScore(scoreData);

            // --- Step 3: Save the Plan ---
            await savePlan(userProfile, planData);

        } catch (error) {
            console.error('An error occurred:', error);
            aiSummaryText.textContent = '';
            healthScoreDisplay.innerHTML = `<p style="color: red;">Could not calculate score.</p>`;
            recommendationsList.innerHTML = `<li style="color: red;"><strong>Error:</strong> ${error.message}</li>`;
        }
    });

    function displayHealthScore(data) {
            let scoreColor = '#F44336'; // Default to Red
            if (data.score > 80) {
                scoreColor = '#4CAF50'; // Green for Excellent
            } else if (data.score > 60) {
                scoreColor = '#FFC107'; // Yellow for Good
            }

        healthScoreDisplay.innerHTML = `
            <div class="score-gauge" style="--score-color: ${scoreColor}; --score-value: ${data.score}">
                <span class="score-value">${data.score}/100</span>
            </div>
            <h4 class="score-rating">${data.rating}</h4>
            <p class="score-feedback">${data.feedback}</p>
        `;
    }

    async function savePlan(profileData, planData) {
        // This function is unchanged
        if (!token) return;
        try {
            await fetch('/api/plans', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    profile_data: profileData,
                    plan_data: planData
                })
            });
        } catch (error) {
            console.error('Error saving plan:', error);
        }
    }

    function displayRecommendations(data) {
        // This function is unchanged
        savingsPotentialSpan.textContent = data.summary.monthly_savings_potential;
        investorProfileSpan.textContent = data.summary.your_investor_profile;
        aiSummaryText.textContent = data.summary.ai_summary;
        recommendationsList.innerHTML = data.recommendations.map(rec => `<li>${rec.replace(/^\s*[\*\-\d]+\.?\s*/, '')}</li>`).join('');
        
        if (portfolioChart) portfolioChart.destroy();
        portfolioChart = new Chart(chartCanvas, {
            type: 'doughnut',
            data: {
                labels: data.portfolio.labels,
                datasets: [{
                    label: 'Portfolio Allocation',
                    data: data.portfolio.data,
                    backgroundColor: ['#0A2540', '#007BFF', '#7AC5F3', '#00A896', '#B3D8F4'],
                    borderColor: '#ffffff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'top' } }
            }
        });
    }
});