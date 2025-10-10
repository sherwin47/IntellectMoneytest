// frontend/js/dashboard.js

document.addEventListener('DOMContentLoaded', () => {
    
    // --- NEW: Function to fetch and display news --
    
    // --- Existing code for recommendations ---
    const financeForm = document.getElementById('finance-form');
    const recommendationOutput = document.getElementById('recommendation-output');
    
    const savingsPotentialSpan = document.getElementById('savings-potential');
    const investorProfileSpan = document.getElementById('investor-profile');
    const aiSummaryText = document.getElementById('ai-summary-text');
    const recommendationsList = document.getElementById('recommendations-list');
    const chartCanvas = document.getElementById('portfolio-chart');
    
    let portfolioChart = null;

    financeForm.addEventListener('submit', async function(event) {
        event.preventDefault();

        const userProfile = {
            income: parseFloat(document.getElementById('monthly-income').value),
            expenses: parseFloat(document.getElementById('monthly-expenses').value),
            savings: parseFloat(document.getElementById('total-savings').value),
            risk_tolerance_input: document.getElementById('risk-tolerance').value
        };

        recommendationOutput.style.display = 'block';
        recommendationsList.innerHTML = '<li>Generating your personalized AI plan...</li>';
        aiSummaryText.textContent = 'Analyzing your profile...';

        try {
            const response = await fetch('https://intellect-money-backend.onrender.com/api/recommendations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userProfile),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Network response was not ok');
            }

            const data = await response.json();
            displayRecommendations(data);

        } catch (error) {
            console.error('Error fetching recommendations:', error);
            aiSummaryText.textContent = '';
            recommendationsList.innerHTML = `<li style="color: red;"><strong>Error:</strong> ${error.message}</li>`;
        }
    });

    function displayRecommendations(data) {
        savingsPotentialSpan.textContent = data.summary.monthly_savings_potential;
        investorProfileSpan.textContent = data.summary.your_investor_profile;
        aiSummaryText.textContent = data.summary.ai_summary;

        if (data.recommendations && data.recommendations.length > 0) {
            recommendationsList.innerHTML = data.recommendations.map(rec => {
                const cleanedRec = rec.replace(/^\s*[\*\-\d]+\.?\s*/, '');
                return `<li>${cleanedRec}</li>`;
            }).join('');
        } else {
            recommendationsList.innerHTML = '<li>No specific actions were recommended.</li>';
        }
        
        if (portfolioChart) {
            portfolioChart.destroy();
        }

        portfolioChart = new Chart(chartCanvas, {
            type: 'doughnut',
            data: {
                labels: data.portfolio.labels,
                datasets: [{
                    label: 'Portfolio Allocation',
                    data: data.portfolio.data,
                    backgroundColor: ['#0A2540', '#007BFF', '#7AC5F3', '#00A896', '#B3D8F4'],
                    borderColor: '#ffffff',
                    borderWidth: 2,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) { label += ': '; }
                                if (context.parsed !== null) { label += context.parsed + '%'; }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }
});