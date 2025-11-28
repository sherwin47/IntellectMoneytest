

document.addEventListener('DOMContentLoaded', () => {
    const plansContainer = document.getElementById('plans-container');
    const modal = document.getElementById('plan-details-modal');
    const modalBody = document.getElementById('modal-body');
    const closeModal = document.querySelector('.close-button');

    const token = localStorage.getItem('userToken');

    async function loadSavedPlans() {
        if (!token) {
            plansContainer.innerHTML = '<p>You must be logged in to view your plans.</p>';
            return;
        }

        try {
            const response = await fetch('http://127.0.0.1:8000/api/plans/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch saved plans.');
            }

            const plans = await response.json();
            displayPlans(plans);

        } catch (error) {
            console.error('Error loading plans:', error);
            plansContainer.innerHTML = `<p>Error loading your plans. Please try again later.</p>`;
        }
    }

    function displayPlans(plans) {
        plansContainer.innerHTML = ''; 

        if (plans.length === 0) {
            plansContainer.innerHTML = '<p>You have no saved plans yet. Go to the dashboard to generate one!</p>';
            return;
        }

        plans.forEach(plan => {
            const planCard = document.createElement('div');
            planCard.className = 'card';
            
            const planDate = new Date(plan.created_at).toLocaleDateString('en-IN', {
                year: 'numeric', month: 'long', day: 'numeric'
            });

            planCard.innerHTML = `
                <h3>Plan from ${planDate}</h3>
                <p>Income: ₹${plan.income.toLocaleString()}</p>
                <p>Expenses: ₹${plan.expenses.toLocaleString()}</p>
                <button class="cta-button view-details-btn">View Details</button>
            `;

            planCard.querySelector('.view-details-btn').addEventListener('click', () => {
                showPlanDetails(plan);
            });

            plansContainer.appendChild(planCard);
        });
    }

    function showPlanDetails(plan) {
        const recommendations = JSON.parse(plan.recommendations_json);
        const portfolio = JSON.parse(plan.portfolio_json);

        modalBody.innerHTML = `
            <h2>Plan Details (${new Date(plan.created_at).toLocaleDateString()})</h2>
            <h4>AI Summary</h4>
            <p>${plan.ai_summary}</p>
            <h4>Recommended Actions</h4>
            <ul>
                ${recommendations.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
            <h4>Suggested Portfolio Allocation</h4>
            <div class="chart-container" style="position: relative; height:300px; width:100%">
                <canvas id="portfolio-chart-modal"></canvas>
            </div>
        `;
        
        modal.style.display = 'block';

        
        new Chart(document.getElementById('portfolio-chart-modal'), {
            type: 'doughnut',
            data: {
                labels: portfolio.labels,
                datasets: [{
                    label: 'Allocation',
                    data: portfolio.data,
                    backgroundColor: ['#4CAF50', '#FFC107', '#2196F3', '#F44336', '#9C27B0'],
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
            }
        });
    }

    
    closeModal.addEventListener('click', () => {
        modal.style.display = 'none';
    });
    window.addEventListener('click', (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    });

    loadSavedPlans();
});