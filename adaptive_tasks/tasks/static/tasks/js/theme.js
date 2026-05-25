(function () {
    const STORAGE_KEY = 'taskPlannerTheme';
    const LIGHT_CLASS = 'theme-light';
    const toggle = document.getElementById('theme-toggle');
    const icon = document.getElementById('theme-toggle-icon');

    function isLightTheme() {
        return document.documentElement.classList.contains(LIGHT_CLASS);
    }

    function updateToggle() {
        const light = isLightTheme();
        if (icon) {
            icon.textContent = light ? '🌙' : '☀️';
        }
        if (toggle) {
            toggle.title = light ? 'Включить тёмную тему' : 'Включить светлую тему';
            toggle.setAttribute('aria-label', toggle.title);
            toggle.setAttribute('aria-pressed', String(light));
        }
    }

    function setTheme(theme) {
        const light = theme === 'light';
        document.documentElement.classList.toggle(LIGHT_CLASS, light);
        try {
            localStorage.setItem(STORAGE_KEY, light ? 'light' : 'dark');
        } catch (e) {}
        updateToggle();
        window.dispatchEvent(new CustomEvent('taskPlannerThemeChange', {
            detail: { theme: light ? 'light' : 'dark' },
        }));
    }

    if (toggle) {
        toggle.addEventListener('click', () => {
            setTheme(isLightTheme() ? 'dark' : 'light');
        });
    }

    updateToggle();
}());
