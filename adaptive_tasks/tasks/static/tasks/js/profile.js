/**
 * Profile dashboard: tabs and charts.
 */

(function () {
    const config = window.PROFILE_CONFIG || {};
    const chartData = Array.isArray(config.chartData) ? config.chartData : [];
    const statusData = config.statusData || {};
    let statusChartInstance = null;
    let planChartInstance = null;

    function isLightTheme() {
        return document.documentElement.classList.contains('theme-light');
    }

    function chartColors() {
        if (isLightTheme()) {
            return {
                text: '#475569',
                title: '#0f172a',
                grid: 'rgba(100,116,139,0.14)',
                surface: 'rgba(255,255,255,0.96)',
                border: 'rgba(100,116,139,0.22)',
                doughnutBorder: 'rgba(248,250,252,0.98)',
            };
        }

        return {
            text: '#94a3b8',
            title: '#f8fafc',
            grid: 'rgba(148,163,184,0.08)',
            surface: 'rgba(15,23,42,0.96)',
            border: 'rgba(148,163,184,0.25)',
            doughnutBorder: 'rgba(15,23,42,0.95)',
        };
    }

    function initTabs() {
        const tabs = Array.from(document.querySelectorAll('.profile-tab'));
        const panels = Array.from(document.querySelectorAll('.tab-panel'));

        tabs.forEach((tab) => {
            tab.addEventListener('click', () => {
                const target = tab.dataset.tab;

                tabs.forEach((item) => item.classList.toggle('is-active', item === tab));
                panels.forEach((panel) => {
                    panel.classList.toggle('is-active', panel.dataset.panel === target);
                });

                if (target === 'history') {
                    initPlanChart();
                }
            });
        });
    }

    function setupChartDefaults() {
        if (!window.Chart) return;
        Chart.defaults.color = chartColors().text;
        Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
    }

    function initStatusChart() {
        const canvas = document.getElementById('statusChart');
        if (!canvas || !window.Chart) return;

        const completed = Number(statusData.completed) || 0;
        const active = Number(statusData.active) || 0;
        const overdue = Number(statusData.overdue) || 0;
        const values = [completed, active, overdue];
        const hasData = values.some((value) => value > 0);

        const colors = chartColors();

        if (statusChartInstance) {
            statusChartInstance.destroy();
        }

        statusChartInstance = new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Выполнено', 'Активно', 'Просрочено'],
                datasets: [{
                    data: hasData ? values : [1],
                    backgroundColor: hasData
                        ? ['#22c55e', '#3b82f6', '#ef4444']
                        : ['rgba(148, 163, 184, 0.22)'],
                    borderColor: colors.doughnutBorder,
                    borderWidth: 5,
                    hoverOffset: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '72%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: hasData,
                        backgroundColor: colors.surface,
                        borderColor: colors.border,
                        borderWidth: 1,
                        titleColor: colors.title,
                        bodyColor: colors.text,
                    },
                },
            },
        });
    }

    function initPlanChart() {
        const canvas = document.getElementById('planChart');
        if (!canvas || !window.Chart || !chartData.length || planChartInstance) return;

        const colors = chartColors();

        planChartInstance = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: chartData.map((item) => item.title),
                datasets: [
                    {
                        label: 'Плановый срок',
                        data: chartData.map((item) => item.planned),
                        backgroundColor: 'rgba(59, 130, 246, 0.65)',
                        borderColor: 'rgba(59, 130, 246, 0.9)',
                        borderWidth: 1,
                        borderRadius: 6,
                        borderSkipped: false,
                    },
                    {
                        label: 'Фактический срок',
                        data: chartData.map((item) => Math.max(0, item.planned + item.delay)),
                        backgroundColor: chartData.map((item) => item.delay > 0
                            ? 'rgba(239, 68, 68, 0.65)'
                            : 'rgba(34, 197, 94, 0.65)'),
                        borderColor: chartData.map((item) => item.delay > 0
                            ? 'rgba(239, 68, 68, 0.9)'
                            : 'rgba(34, 197, 94, 0.9)'),
                        borderWidth: 1,
                        borderRadius: 6,
                        borderSkipped: false,
                    },
                ],
            },
            options: {
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        labels: { color: colors.text, padding: 18, usePointStyle: true },
                    },
                    tooltip: {
                        backgroundColor: colors.surface,
                        borderColor: colors.border,
                        borderWidth: 1,
                        titleColor: colors.title,
                        bodyColor: colors.text,
                        callbacks: {
                            afterBody(items) {
                                const delay = chartData[items[0].dataIndex].delay;
                                if (delay > 0) return [`Просрочено на: +${delay} дн.`];
                                if (delay < 0) return [`Выполнено раньше на: ${Math.abs(delay)} дн.`];
                                return ['Выполнено точно в срок'];
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        ticks: { color: colors.text, maxRotation: 30 },
                        grid: { color: colors.grid },
                    },
                    y: {
                        ticks: { color: colors.text },
                        grid: { color: colors.grid },
                        title: { display: true, text: 'Дней', color: colors.text },
                        beginAtZero: true,
                    },
                },
            },
        });
    }

    function refreshCharts() {
        setupChartDefaults();
        if (statusChartInstance) {
            statusChartInstance.destroy();
            statusChartInstance = null;
        }
        if (planChartInstance) {
            planChartInstance.destroy();
            planChartInstance = null;
        }
        initStatusChart();
        if (document.querySelector('[data-panel="history"].is-active')) {
            initPlanChart();
        }
    }

    initTabs();
    setupChartDefaults();
    initStatusChart();
    if (document.querySelector('[data-panel="history"].is-active')) {
        initPlanChart();
    }
    window.addEventListener('taskPlannerThemeChange', refreshCharts);
}());
