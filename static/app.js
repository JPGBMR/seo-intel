window.TMF = (function () {
    function initSearch() {
        const input = document.getElementById('topicSearch');
        const table = document.getElementById('topicsTable');
        if (!input || !table) {
            return;
        }
        input.addEventListener('input', function () {
            const query = this.value.trim().toLowerCase();
            table.querySelectorAll('tbody tr').forEach((row) => {
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    }

    function renderChart(canvasId, chartData) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !chartData || !chartData.labels || !chartData.labels.length) {
            return;
        }
        const ctx = canvas.getContext('2d');
        if (!ctx) {
            return;
        }
        if (canvas.chartInstance) {
            canvas.chartInstance.destroy();
        }
        canvas.chartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: 'Trend Score',
                        data: chartData.scores,
                        backgroundColor: '#0d6efd',
                        borderRadius: 6,
                    },
                ],
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => 'Trend Score: ' + context.parsed.x,
                        },
                    },
                },
                scales: {
                    x: {
                        suggestedMin: 0,
                        suggestedMax: 100,
                        grid: { color: '#e9edf5' },
                    },
                    y: {
                        ticks: { autoSkip: false },
                        grid: { display: false },
                    },
                },
            },
        });
    }

    document.addEventListener('DOMContentLoaded', initSearch);

    return { renderChart };
})();
