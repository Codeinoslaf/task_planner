(function () {
    const SEEN_STORAGE_KEY = 'taskPlannerSeenNotifications';
    const CHECK_INTERVAL_MS = 60000;

    const urgencyCfg = {
        critical: {
            bg: 'rgba(239,68,68,0.12)',
            border: 'rgba(239,68,68,0.4)',
            color: '#fca5a5',
            icon: '🚨',
        },
        high: {
            bg: 'rgba(251,191,36,0.12)',
            border: 'rgba(251,191,36,0.4)',
            color: '#fde68a',
            icon: '⚠️',
        },
        medium: {
            bg: 'rgba(59,130,246,0.12)',
            border: 'rgba(59,130,246,0.4)',
            color: '#93c5fd',
            icon: '🔔',
        },
    };

    function getSeenNotifications() {
        try {
            return new Set(JSON.parse(sessionStorage.getItem(SEEN_STORAGE_KEY) || '[]'));
        } catch (e) {
            return new Set();
        }
    }

    function saveSeenNotifications(seen) {
        sessionStorage.setItem(SEEN_STORAGE_KEY, JSON.stringify(Array.from(seen)));
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function getNotificationText(notification) {
        if (notification.message) return notification.message;
        if (notification.time_left) return `Через ${notification.time_left}`;
        return 'Есть новое уведомление';
    }

    window.toggleNotifPanel = function () {
        document.getElementById('notif-panel').classList.toggle('active');
    };

    document.addEventListener('click', function (e) {
        const wrapper = document.getElementById('notif-wrapper');
        if (wrapper && !wrapper.contains(e.target)) {
            document.getElementById('notif-panel').classList.remove('active');
        }
    });

    function renderPanel(notifications) {
        const badge = document.getElementById('notif-badge');
        const bell = document.getElementById('notif-bell-btn');
        const list = document.getElementById('notif-list');

        if (!badge || !bell || !list) return;

        if (notifications.length > 0) {
            badge.textContent = notifications.length;
            badge.style.display = 'flex';
            bell.classList.add('notif-bell-btn--active');
        } else {
            badge.style.display = 'none';
            bell.classList.remove('notif-bell-btn--active');
            list.innerHTML = '<div class="notif-empty">Нет актуальных уведомлений</div>';
            return;
        }

        list.innerHTML = notifications.map((notification) => {
            const cfg = urgencyCfg[notification.urgency] || urgencyCfg.medium;
            const title = escapeHtml(notification.title);
            const text = escapeHtml(getNotificationText(notification));

            return `<div class="notif-item" style="background:${cfg.bg};border-color:${cfg.border}">
                <span class="notif-item__icon">${cfg.icon}</span>
                <div class="notif-item__body">
                    <div class="notif-item__title">${title}</div>
                    <div class="notif-item__time" style="color:${cfg.color}">${text}</div>
                </div>
            </div>`;
        }).join('');
    }

    function showToast(notification) {
        const stack = document.getElementById('notif-toast-stack');
        if (!stack) return;

        const cfg = urgencyCfg[notification.urgency] || urgencyCfg.medium;
        const toast = document.createElement('div');
        toast.className = `notif-toast notif-toast--${notification.urgency || 'medium'}`;
        toast.innerHTML = `
            <div class="notif-toast__icon">${cfg.icon}</div>
            <div class="notif-toast__body">
                <div class="notif-toast__title">${escapeHtml(notification.title)}</div>
                <div class="notif-toast__text">${escapeHtml(getNotificationText(notification))}</div>
            </div>
            <button class="notif-toast__close" type="button" aria-label="Закрыть">×</button>
        `;

        const removeToast = () => {
            toast.classList.add('notif-toast--hide');
            setTimeout(() => toast.remove(), 220);
        };

        toast.querySelector('.notif-toast__close').addEventListener('click', removeToast);
        stack.appendChild(toast);
        setTimeout(removeToast, 7000);
    }

    function showNewToasts(notifications) {
        const seen = getSeenNotifications();

        notifications.forEach((notification) => {
            if (!notification.id || seen.has(notification.id)) return;
            seen.add(notification.id);
            showToast(notification);
        });

        saveSeenNotifications(seen);
    }

    window.loadNotifications = function () {
        fetch('/api/notifications/')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data || !Array.isArray(data.notifications)) return;
                renderPanel(data.notifications);
                showNewToasts(data.notifications);
            })
            .catch(() => {
                const list = document.getElementById('notif-list');
                if (list) list.innerHTML = '<div class="notif-empty">Не удалось загрузить</div>';
            });
    };

    window.loadNotifications();
    setInterval(window.loadNotifications, CHECK_INTERVAL_MS);
}());
