document.addEventListener('DOMContentLoaded', () => {
    // 1. Authentication Check
    const token = localStorage.getItem('userToken');
    if (!token) {
        window.location.href = 'login.html';
    }

    // 2. DOM Elements
    const financeForm = document.getElementById('finance-form');
    const recommendationOutput = document.getElementById('recommendation-output');
    
    // Output Fields
    const savingsPotentialSpan = document.getElementById('savings-potential');
    const investorProfileSpan = document.getElementById('investor-profile');
    const aiSummaryText = document.getElementById('ai-summary-text');
    const recommendationsList = document.getElementById('recommendations-list');
    const chartCanvas = document.getElementById('portfolio-chart');
    const healthScoreDisplay = document.getElementById('health-score-display');
    const alertsContainer = document.getElementById('agent-alerts-container'); // Agentic UI

    let portfolioChart = null;

    // 3. Inject CSS Animation for Alerts (One-time setup)
    const styleSheet = document.createElement("style");
    styleSheet.innerText = `
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    `;
    document.head.appendChild(styleSheet);

    // 4. Main Form Submission Handler
    financeForm.addEventListener('submit', async function(event) {
        event.preventDefault();

        // Collect User Input
        const userProfile = {
            income: parseFloat(document.getElementById('monthly-income').value),
            expenses: parseFloat(document.getElementById('monthly-expenses').value),
            savings: parseFloat(document.getElementById('total-savings').value),
            financial_goal: document.getElementById('financial-goal').value || "General Wealth Building",
            risk_tolerance_input: document.getElementById('risk-tolerance').value
        };

        // UI Loading State
        recommendationOutput.style.display = 'block';
        healthScoreDisplay.innerHTML = '<p>Calculating...</p>';
        recommendationsList.innerHTML = '<li>Generating your personalized AI plan...</li>';
        aiSummaryText.textContent = 'Analyzing your profile...';
        if(alertsContainer) alertsContainer.innerHTML = ''; // Clear old alerts

        try {
            // --- A. Fetch Recommendations (and Alerts) ---
            const recommendationsResponse = await fetch('http://127.0.0.1:8000/api/recommendations', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    // --- NEW LINE: Sends your ID so the AI can remember you ---
                    'Authorization': `Bearer ${token}` 
                },
                body: JSON.stringify(userProfile),
            });

            if (!recommendationsResponse.ok) {
                const errorData = await recommendationsResponse.json();
                throw new Error(errorData.detail || 'Failed to fetch recommendations');
            }
            
            const planData = await recommendationsResponse.json();
            
            // Display Data
            displayRecommendations(planData);
            
            // ** AGENTIC AI FEATURE **
            // Check if the backend sent proactive alerts
            if (planData.alerts && planData.alerts.length > 0) {
                displayAgentAlerts(planData.alerts);
            }

            // --- B. Fetch Health Score ---
            const healthScoreResponse = await fetch('http://127.0.0.1:8000/api/health-score', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userProfile),
            });

            if (!healthScoreResponse.ok) throw new Error('Failed to calculate health score.');
            const scoreData = await healthScoreResponse.json();
            displayHealthScore(scoreData);

            // --- C. Save Plan to Database ---
            await savePlan(userProfile, planData);

        } catch (error) {
            console.error('An error occurred:', error);
            aiSummaryText.textContent = 'An error occurred while generating your plan.';
            healthScoreDisplay.innerHTML = `<p style="color: #ff6b6b;">Could not calculate score.</p>`;
            recommendationsList.innerHTML = `<li style="color: #ff6b6b;"><strong>Error:</strong> ${error.message}</li>`;
        }
    });

    // --- Helper Function: Display Agent Alerts ---
    function displayAgentAlerts(alerts) {
        if (!alertsContainer) return;
        alertsContainer.innerHTML = ''; // Clear previous

        alerts.forEach(alert => {
            const div = document.createElement('div');
            
            // Dynamic Styles based on Alert Type
            let colorClass = '';
            if(alert.type === 'danger') colorClass = 'background: rgba(220, 53, 69, 0.2); border: 1px solid #dc3545; color: #ff6b6b;';
            else if(alert.type === 'warning') colorClass = 'background: rgba(255, 193, 7, 0.2); border: 1px solid #ffc107; color: #ffda6a;';
            else if(alert.type === 'success') colorClass = 'background: rgba(40, 167, 69, 0.2); border: 1px solid #28a745; color: #75b798;';

            div.style.cssText = `
                ${colorClass}
                padding: 15px;
                border-radius: 12px;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 15px;
                animation: slideDown 0.5s ease-out;
            `;

            div.innerHTML = `
                <span style="font-size: 1.5rem;">${alert.icon}</span>
                <div>
                    <strong style="display:block; margin-bottom:2px;">AI Insight:</strong>
                    <span style="font-size: 0.95rem;">${alert.message}</span>
                </div>
            `;

            alertsContainer.appendChild(div);
        });
    }

    // --- Helper Function: Display Health Score Gauge ---
    function displayHealthScore(data) {
        let scoreColor = '#F44336'; // Red
        if (data.score > 80) scoreColor = '#4CAF50'; // Green
        else if (data.score > 60) scoreColor = '#FFC107'; // Yellow

        healthScoreDisplay.innerHTML = `
            <div class="score-gauge" style="--score-color: ${scoreColor}; --score-value: ${data.score}">
                <span class="score-value">${data.score}/100</span>
            </div>
            <h4 class="score-rating" style="color:${scoreColor}">${data.rating}</h4>
            <p class="score-feedback">${data.feedback}</p>
        `;
    }

    // --- Helper Function: Display Text & Chart ---
    function displayRecommendations(data) {
        savingsPotentialSpan.textContent = data.summary.monthly_savings_potential;
        investorProfileSpan.textContent = data.summary.your_investor_profile;
        aiSummaryText.textContent = data.summary.ai_summary;
        
        // --- SMART FORMATTER START ---
        recommendationsList.innerHTML = data.recommendations
            .map(rec => {
                let formattedText = rec;

                // 1. Convert Markdown Bold (**text**) to HTML Bold (<strong>text</strong>)
                formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong style="color: #2c9cff;">$1</strong>');

                // 2. Convert New Lines to <br> for spacing
                formattedText = formattedText.replace(/\n/g, '<br>');

                // 3. Highlight numbers (e.g., "1.") for better readability
                formattedText = formattedText.replace(/^(\d+\.)/, '<span style="color: #00d2ff; font-weight:bold; margin-right:5px;">$1</span>');

                // 4. Return as a list item with extra spacing
                return `<li style="margin-bottom: 20px; line-height: 1.6;">${formattedText}</li>`;
            })
            .join('');
        // --- SMART FORMATTER END ---
        
        // Render Chart.js
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
                maintainAspectRatio: false,
                plugins: { legend: { position: 'right', labels: { color: 'white' } } }
            }
        });
    }

    // --- Helper Function: Save Plan to DB ---
    async function savePlan(profileData, planData) {
        if (!token) return;
        try {
            await fetch('http://127.0.0.1:8000/api/plans', {
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
});