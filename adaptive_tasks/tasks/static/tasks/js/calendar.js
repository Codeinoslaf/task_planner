/**
 * calendar.js — логика страницы календаря
 * Данные из Django-шаблона передаются через window.CALENDAR_CONFIG
 */

const { tasksData, csrfToken } = window.CALENDAR_CONFIG;

const MONTH_NAMES = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
];

let selectedDate     = null;
let currentTimeValue = '';
let aiHintTimer      = null;

// Восстанавливаем позицию навигации из localStorage
let currentDate = new Date();
(function restoreNav() {
    const y = parseInt(localStorage.getItem('cal_year'));
    const m = parseInt(localStorage.getItem('cal_month'));
    if (!isNaN(y) && !isNaN(m) && m >= 0 && m <= 11) {
        currentDate = new Date(y, m, 1);
    }
}());

// ── Вспомогательные ───────────────────────────────────────────────────────────

function getNowTime() {
    const n = new Date();
    return `${String(n.getHours()).padStart(2, '0')}:${String(n.getMinutes()).padStart(2, '0')}`;
}

function getLocalDate(isoString) {
    const d = new Date(isoString);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function formatDate(dateStr) {
    const d = new Date(dateStr + 'T00:00:00');
    return `${d.getDate()} ${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`;
}

function formatEffort(minutes) {
    if (!minutes) return '~0 мин';
    if (minutes < 60) return `~${minutes} мин`;
    const hours = minutes / 60;
    return Number.isInteger(hours) ? `~${hours} ч` : `~${hours.toFixed(1)} ч`;
}

function getDayLoad(tasks) {
    const count = tasks.length;
    const minutes = tasks.reduce((sum, task) => sum + (Number(task.estimated_minutes) || 60), 0);

    if (count >= 4 || minutes >= 300) {
        return {
            level: 'overload',
            label: 'перегруз',
            title: 'День перегружен',
            text: 'Лучше не добавлять сюда сложные дедлайны.',
        };
    }
    if (count >= 2 || minutes >= 150) {
        return {
            level: 'busy',
            label: 'занят',
            title: 'День занят',
            text: 'Короткую задачу добавить можно, сложную лучше проверить.',
        };
    }
    if (count === 1 || minutes > 0) {
        return {
            level: 'light',
            label: 'есть дела',
            title: 'День почти свободен',
            text: 'Нагрузка небольшая.',
        };
    }
    return {
        level: 'free',
        label: 'свободно',
        title: 'День свободен',
        text: 'Можно спокойно планировать новый дедлайн.',
    };
}

function isTaskCompleted(task) {
    return task.status === 'completed';
}

function getActiveTasks(tasks) {
    return tasks.filter(task => !isTaskCompleted(task));
}

function sortTasksForPanel(tasks) {
    return [...tasks].sort((a, b) => {
        if (isTaskCompleted(a) !== isTaskCompleted(b)) {
            return isTaskCompleted(a) ? 1 : -1;
        }
        return new Date(a.planned_deadline) - new Date(b.planned_deadline);
    });
}

// ── Time picker ───────────────────────────────────────────────────────────────

function renderDisplayInput(digits) {
    const d = (i) => digits[i] !== undefined ? digits[i] : null;
    const cur = digits.length;
    const h1 = d(0) ?? (cur === 0 ? '<span class="blink">_</span>' : '_');
    const h2 = d(1) ?? (cur === 1 ? '<span class="blink">_</span>' : '_');
    const m1 = d(2) ?? (cur === 2 ? '<span class="blink">_</span>' : '_');
    const m2 = d(3) ?? (cur === 3 ? '<span class="blink">_</span>' : '_');
    return `${h1}${h2}<span class="colon">:</span>${m1}${m2}`;
}

function renderDisplayStatic(time) {
    const [h, m] = time.split(':');
    return `${h}<span class="colon">:</span>${m}`;
}

function parseTimeValue(time) {
    const match = /^([0-1][0-9]|2[0-3]):([0-5][0-9])$/.exec(time || '');
    if (!match) return null;
    return {
        hours: Number(match[1]),
        minutes: Number(match[2]),
    };
}

function formatTimeValue(hours, minutes) {
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
}

function setTimeValue(hours, minutes) {
    currentTimeValue = formatTimeValue(hours, minutes);
    document.getElementById('time-hidden-input').value = '';
    document.getElementById('time-display').innerHTML = renderDisplayStatic(currentTimeValue);
    document.getElementById('time-error').classList.remove('active');
    setConfirmBtn(true);
}

function showTimeError(message) {
    const error = document.getElementById('time-error');
    error.innerHTML = message;
    error.classList.add('active');
}

function focusHiddenInput() {
    document.getElementById('time-hidden-input').focus();
}

function setConfirmBtn(enabled) {
    const btn = document.getElementById('confirm-time-btn');
    btn.style.opacity      = enabled ? '1' : '0.4';
    btn.style.pointerEvents = enabled ? 'auto' : 'none';
}

function openTimePopup() {
    const existingValue = document.getElementById('time-input').value;
    const initTime = existingValue || getNowTime();

    const hiddenInput = document.getElementById('time-hidden-input');
    hiddenInput.value = '';

    const parsed = parseTimeValue(initTime) || parseTimeValue(getNowTime());
    setTimeValue(parsed.hours, parsed.minutes);

    document.getElementById('time-popup-overlay').classList.add('active');
    document.getElementById('time-popup').classList.add('active');
    setTimeout(() => hiddenInput.focus(), 100);
}

function closeTimePopup() {
    document.getElementById('time-popup-overlay').classList.remove('active');
    document.getElementById('time-popup').classList.remove('active');
    document.getElementById('time-error').classList.remove('active');
}

function confirmTime() {
    if (!parseTimeValue(currentTimeValue)) return;
    document.getElementById('time-input').value = currentTimeValue;
    document.getElementById('task-time').value  = currentTimeValue;
    document.getElementById('time-input').classList.remove('error');
    closeTimePopup();
    fetchAiHint();
}

function setQuickTime(type) {
    const now = new Date();
    let h, m;
    switch (type) {
        case 'now':     h = now.getHours();  m = now.getMinutes(); break;
        case 'morning':  h = 9;  m = 0; break;
        case 'noon':     h = 13; m = 0; break;
        case 'evening':  h = 17; m = 0; break;
        default: return;
    }
    setTimeValue(h, m);
    setTimeout(() => document.getElementById('time-hidden-input').focus(), 50);
}

function addTimeMinutes(deltaMinutes) {
    const parsed = parseTimeValue(currentTimeValue) || parseTimeValue(getNowTime());
    const nextTotal = parsed.hours * 60 + parsed.minutes + deltaMinutes;

    if (nextTotal < 0 || nextTotal > 23 * 60 + 59) {
        showTimeError('Время должно оставаться в выбранном дне');
        return;
    }

    const hours = Math.floor(nextTotal / 60);
    const minutes = nextTotal % 60;
    setTimeValue(hours, minutes);
    setTimeout(() => document.getElementById('time-hidden-input').focus(), 50);
}

function validateTimeRealtime(formatted) {
    const error    = document.getElementById('time-error');
    if (!parseTimeValue(formatted)) {
        const [h, m] = formatted.split(':');
        let msg = '⚠️ Неверный формат времени';
        if (parseInt(h) > 23) msg = '⚠️ Часы не могут быть больше 23';
        else if (parseInt(m) > 59) msg = '⚠️ Минуты не могут быть больше 59';
        error.innerHTML = msg;
        error.classList.add('active');
        setConfirmBtn(false);
    } else {
        error.classList.remove('active');
        setConfirmBtn(true);
    }
}

// Ввод времени с клавиатуры
const hiddenInput = document.getElementById('time-hidden-input');

hiddenInput.addEventListener('input', function (e) {
    let value = e.target.value.replace(/[^\d]/g, '');
    if (value.length > 4) value = value.slice(0, 4);
    e.target.value = value;

    document.getElementById('time-display').innerHTML = renderDisplayInput(value.split(''));

    if (value.length === 4) {
        const formatted = value.slice(0, 2) + ':' + value.slice(2);
        currentTimeValue = formatted;
        validateTimeRealtime(formatted);
    } else {
        currentTimeValue = '';
        document.getElementById('time-error').classList.remove('active');
        setConfirmBtn(true);
    }
});

hiddenInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter')  { e.preventDefault(); confirmTime(); }
    if (e.key === 'Escape') { e.preventDefault(); closeTimePopup(); }
});

document.getElementById('time-popup').addEventListener('click', function (e) {
    if (!e.target.closest('button')) focusHiddenInput();
});

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && document.getElementById('time-popup').classList.contains('active')) {
        closeTimePopup();
    }
});

// ── AI-подсказки ──────────────────────────────────────────────────────────────

function fetchAiHint() {
    if (!selectedDate) return;
    const timeValue = document.getElementById('task-time').value || getNowTime();
    const plannedDeadline = `${selectedDate}T${timeValue}:00`;
    const title = document.getElementById('task-title').value || '';
    const description = document.getElementById('task-description').value || '';
    const taskId = document.getElementById('task-id').value || '';
    const block    = document.getElementById('ai-hint-block');
    const content  = document.getElementById('ai-hint-content');

    content.innerHTML = '<div class="ai-hint-loader">Анализирую историю...</div>';
    block.style.display = 'block';

    clearTimeout(aiHintTimer);
    aiHintTimer = setTimeout(() => {
        const params = new URLSearchParams({
            planned_deadline: plannedDeadline,
            title,
            description,
        });
        if (taskId) params.set('task_id', taskId);

        fetch(`/api/ai-hint/?${params.toString()}`)
            .then(r => r.ok ? r.json() : null)
            .then(data => renderAiHint(data))
            .catch(() => { block.style.display = 'none'; });
    }, 350);
}

function escapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function renderAiHint(data) {
    const block   = document.getElementById('ai-hint-block');
    const content = document.getElementById('ai-hint-content');

    if (!data) {
        block.style.display = 'none';
        return;
    }

    const riskMeta = {
        high: {
            label: 'Высокий риск',
            className: 'ai-risk-summary--high',
        },
        medium: {
            label: 'Средний риск',
            className: 'ai-risk-summary--medium',
        },
        low: {
            label: 'Низкий риск',
            className: 'ai-risk-summary--low',
        },
    };

    const riskStyle = {
        high:   'background:rgba(239,68,68,0.12);border-color:#ef4444;color:#fca5a5',
        medium: 'background:rgba(251,191,36,0.12);border-color:#fbbf24;color:#fde68a',
        low:    'background:rgba(34,197,94,0.12);border-color:#22c55e;color:#86efac',
    };

    const iconByKind = {
        deadline: '⏳',
        day: '📅',
        day_load: '📌',
        time_slot: '🕒',
    };

    const cards = Array.isArray(data.cards) && data.cards.length > 0
        ? data.cards
        : [{
            kind: 'deadline',
            level: 'medium',
            title: 'Пока мало данных',
            text: 'Система накопит историю после завершения нескольких задач и начнет давать точнее рекомендации.',
        }];

    const isDayMode = data.assessment_mode === 'day_context';
    const meta = riskMeta[data.risk_level] || riskMeta.medium;
    const reasons = Array.isArray(data.risk_reasons) && data.risk_reasons.length > 0
        ? `<ul class="ai-risk-reasons">${data.risk_reasons.map(reason => `<li>${escapeHtml(reason)}</li>`).join('')}</ul>`
        : '';
    const riskScore = Number.isFinite(Number(data.risk_score)) ? Number(data.risk_score) : 50;
    const summaryClass = isDayMode ? 'ai-risk-summary--day' : meta.className;
    const scoreHtml = isDayMode ? '' : `<div class="ai-risk-summary__score">${riskScore}%</div>`;
    const meterHtml = isDayMode ? '' : `<div class="ai-risk-meter"><span style="width:${Math.max(4, Math.min(100, riskScore))}%"></span></div>`;
    const summaryLabel = isDayMode ? 'Оценка выбранного дня' : meta.label;
    const summary = `<div class="ai-risk-summary ${summaryClass}">
        <div class="ai-risk-summary__top">
            <div>
                <div class="ai-risk-summary__label">${summaryLabel}</div>
                <div class="ai-risk-summary__title">${escapeHtml(data.risk_title || 'Оценка дедлайна')}</div>
            </div>
            ${scoreHtml}
        </div>
        ${meterHtml}
        <div class="ai-risk-summary__text">${escapeHtml(data.risk_text || '')}</div>
        ${reasons}
    </div>`;

    const profile = data.task_profile || null;
    const profileHtml = profile && profile.has_text
        ? `<div class="ai-task-profile">
            <div class="ai-task-profile__label">Система распознала</div>
            <div class="ai-task-profile__chips">
                <span>${escapeHtml(profile.context_label)}</span>
                <span>${escapeHtml(profile.estimated_label)}</span>
                <span>${escapeHtml(profile.difficulty_label)}</span>
            </div>
        </div>`
        : '';

    let cardsHtml = cards.map(card => {
        const style = riskStyle[card.level] || riskStyle.medium;
        const icon = iconByKind[card.kind] || '💡';
        let action = '';
        if (card.action_text && card.suggested_date) {
            action = `<button type="button" class="ai-hint-action" onclick="applyAiHintDate('${card.suggested_date}')">${escapeHtml(card.action_text)}</button>`;
        } else if (card.action_text && card.suggested_time) {
            action = `<button type="button" class="ai-hint-action" onclick="applyAiHintTime('${card.suggested_time}')">${escapeHtml(card.action_text)}</button>`;
        }
        return `<div class="ai-hint-item" style="${style}">
            <div class="ai-hint-title">${icon} ${escapeHtml(card.title)}</div>
            <div class="ai-hint-text">${escapeHtml(card.text)}</div>
            ${action}
        </div>`;
    }).join('');

    content.innerHTML = `${profileHtml}${summary}<div class="ai-hint-list">${cardsHtml}</div>`;
    block.style.display = 'block';
}

function applyAiHintDate(dateStr) {
    selectedDate = dateStr;
    document.getElementById('selected-date-display').textContent = formatDate(dateStr);
    fetchAiHint();
}

function applyAiHintTime(timeStr) {
    document.getElementById('time-input').value = timeStr;
    document.getElementById('task-time').value = timeStr;
    fetchAiHint();
}

// ── Форма ─────────────────────────────────────────────────────────────────────

document.getElementById('task-form').addEventListener('submit', function (e) {
    e.preventDefault();
    const timeValue = document.getElementById('task-time').value;
    if (!timeValue) {
        document.getElementById('time-input').classList.add('error');
        openTimePopup();
        return;
    }
    document.getElementById('hidden-deadline').value = `${selectedDate}T${timeValue}:00`;
    this.submit();
});

['task-title', 'task-description'].forEach((id) => {
    document.getElementById(id).addEventListener('input', fetchAiHint);
});

// ── Календарь ─────────────────────────────────────────────────────────────────

function renderCalendar() {
    const year  = currentDate.getFullYear();
    const month = currentDate.getMonth();
    localStorage.setItem('cal_year', year);
    localStorage.setItem('cal_month', month);
    document.getElementById('current-month-year').textContent = `${MONTH_NAMES[month]} ${year}`;

    const firstDayWeek   = (new Date(year, month, 1).getDay() || 7);
    const daysInMonth    = new Date(year, month + 1, 0).getDate();
    const daysInPrevMonth = new Date(year, month, 0).getDate();
    const calendarDays   = document.getElementById('calendar-days');
    calendarDays.innerHTML = '';

    for (let i = firstDayWeek - 1; i > 0; i--) {
        calendarDays.innerHTML += `<div class="calendar-day calendar-day--other-month"><div class="day-number">${daysInPrevMonth - i + 1}</div></div>`;
    }

    const today = new Date();
    for (let day = 1; day <= daysInMonth; day++) {
        const isToday  = new Date(year, month, day).toDateString() === today.toDateString();
        const dateStr  = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const dayTasks = tasksData.filter(t => getLocalDate(t.planned_deadline) === dateStr);
        const activeTasks = getActiveTasks(dayTasks);
        const completedCount = dayTasks.length - activeTasks.length;
        const count    = activeTasks.length;
        const load     = getDayLoad(activeTasks);
        const word     = count === 1 ? 'задача' : count < 5 ? 'задачи' : 'задач';
        const doneClass = count === 0 && completedCount > 0 ? ' calendar-day--done' : '';
        const completedClass = completedCount > 0 ? ' calendar-day--has-completed' : '';
        const classes  = `calendar-day calendar-day--${load.level}${doneClass}${completedClass}${isToday ? ' calendar-day--today' : ''}${count > 0 ? ' calendar-day--has-tasks' : ''}`;
        const completedMark = count > 0 && completedCount > 0
            ? `<div class="task-completed-mark" title="Выполнено: ${completedCount}">✓ ${completedCount}</div>`
            : '';
        const countHtml = count > 0
            ? `${completedMark}<div class="task-count">${count} ${word}</div><div class="day-load-badge">${load.label}</div>`
            : completedCount > 0
                ? `<div class="task-count task-count--done">✓ ${completedCount}</div><div class="day-load-badge day-load-badge--done">готово</div>`
                : '';
        calendarDays.innerHTML += `<div class="${classes}" onclick="openPanel('${dateStr}')"><div class="day-number">${day}</div>${countHtml}</div>`;
    }

    const remaining = (7 - (calendarDays.children.length % 7)) % 7;
    for (let day = 1; day <= remaining; day++) {
        calendarDays.innerHTML += `<div class="calendar-day calendar-day--other-month"><div class="day-number">${day}</div></div>`;
    }
}

function openPanel(dateStr) {
    selectedDate = dateStr;
    document.getElementById('side-panel').classList.add('side-panel--active');
    document.getElementById('calendar-shell').classList.add('calendar-shell--shifted');

    const tasks     = sortTasksForPanel(tasksData.filter(t => getLocalDate(t.planned_deadline) === dateStr));
    const activeTasks = getActiveTasks(tasks);
    const completedCount = tasks.length - activeTasks.length;
    const tasksList = document.getElementById('panel-tasks-list');
    const load      = getDayLoad(activeTasks);
    const dashboardLevel = activeTasks.length === 0 && completedCount > 0 ? 'done' : load.level;
    const dashboardLabel = activeTasks.length === 0 && completedCount > 0 ? 'готово' : load.label;
    const dashboardTitle = activeTasks.length === 0 && completedCount > 0 ? 'Все дедлайны выполнены' : load.title;
    const dashboardText = activeTasks.length === 0 && completedCount > 0 ? 'На этот день активных задач не осталось.' : load.text;
    const effort    = activeTasks.reduce((sum, task) => sum + (Number(task.estimated_minutes) || 60), 0);
    const word      = activeTasks.length === 1 ? 'дедлайн' : activeTasks.length < 5 ? 'дедлайна' : 'дедлайнов';
    const completedText = completedCount > 0 ? ` · выполнено: ${completedCount}` : '';
    const dayDashboard = `
        <div class="panel-day-dashboard panel-day-dashboard--${dashboardLevel}">
            <div>
                <div class="panel-day-dashboard__label">${dashboardLabel}</div>
                <div class="panel-day-dashboard__title">${dashboardTitle}</div>
                <div class="panel-day-dashboard__text">${activeTasks.length} ${word} · ${formatEffort(effort)}${completedText}. ${dashboardText}</div>
            </div>
            <button type="button" class="panel-day-dashboard__add" onclick="showNewTaskForm('${dateStr}')">+ Добавить</button>
        </div>`;

    if (tasks.length > 0) {
        document.getElementById('panel-tasks-section').style.display = 'flex';
        document.getElementById('task-form').style.display = 'none';
        document.getElementById('panel-title').textContent = 'Задачи';
        document.getElementById('selected-date-display').textContent = formatDate(dateStr);

        tasksList.innerHTML = dayDashboard + tasks.map(task => `
            <div class="panel-task-item${isTaskCompleted(task) ? ' panel-task-item--completed' : ''}">
                <div class="panel-task-title">${task.title}</div>
                <div class="panel-task-time">🕐 ${new Date(task.planned_deadline).toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit'})} · ${formatEffort(Number(task.estimated_minutes) || 60)}</div>
                ${task.description ? `<p style="font-size:13px;color:#94a3b8;margin:8px 0 0">${task.description}</p>` : ''}
                <div class="panel-task-actions">
                    <button class="task-action-btn task-action-btn--edit" onclick="editTask(${task.id}, event)">✏️ Изменить</button>
                    ${task.status !== 'completed'
                        ? `<button class="task-action-btn task-action-btn--complete" onclick="completeTask(${task.id})">✓ Завершить</button>`
                        : `<span style="color:#86efac;font-size:13px;padding:8px">✓ Выполнено</span>`}
                    <button class="task-action-btn task-action-btn--delete" onclick="deleteTask(${task.id})">🗑 Удалить</button>
                </div>
            </div>`).join('');

    } else {
        showNewTaskForm(dateStr);
    }
}

function showNewTaskForm(dateStr) {
    const timeStr = getNowTime();
    document.getElementById('task-form').style.display = 'flex';
    document.getElementById('panel-tasks-section').style.display = 'none';
    document.getElementById('panel-title').textContent = 'Новая задача';
    document.getElementById('selected-date-display').textContent = formatDate(dateStr);
    document.getElementById('task-form').reset();
    document.getElementById('task-id').value    = '';
    document.getElementById('time-input').value = timeStr;
    document.getElementById('task-time').value  = timeStr;
    document.getElementById('time-input').classList.remove('error');
    document.getElementById('submit-btn-text').textContent = '💾 Сохранить';
    document.getElementById('ai-hint-block').style.display = 'none';
    selectedDate = dateStr;
    fetchAiHint();
}

function editTask(taskId, event) {
    event.stopPropagation();
    const task = tasksData.find(t => t.id === taskId);
    if (!task) return;

    const taskDate    = new Date(task.planned_deadline);
    const localDateStr = getLocalDate(task.planned_deadline);
    const timeStr     = taskDate.toTimeString().slice(0, 5);

    document.getElementById('task-form').style.display = 'flex';
    document.getElementById('panel-tasks-section').style.display = 'none';
    document.getElementById('panel-title').textContent = 'Редактирование';
    document.getElementById('selected-date-display').textContent = formatDate(localDateStr);
    document.getElementById('task-id').value          = task.id;
    document.getElementById('task-title').value       = task.title;
    document.getElementById('task-description').value = task.description || '';
    document.getElementById('time-input').value       = timeStr;
    document.getElementById('task-time').value        = timeStr;
    document.getElementById('time-input').classList.remove('error');
    document.getElementById('submit-btn-text').textContent = '💾 Сохранить изменения';
    document.getElementById('ai-hint-block').style.display = 'none';
    selectedDate = localDateStr;
    fetchAiHint();
}

function closePanel() {
    document.getElementById('side-panel').classList.remove('side-panel--active');
    document.getElementById('calendar-shell').classList.remove('calendar-shell--shifted');
}

function previousMonth() { currentDate.setMonth(currentDate.getMonth() - 1); renderCalendar(); }
function nextMonth()     { currentDate.setMonth(currentDate.getMonth() + 1); renderCalendar(); }
function goToday()       { currentDate = new Date(); renderCalendar(); }

function completeTask(taskId) {
    fetch(`/task/${taskId}/complete/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
    }).then((response) => {
        if (response.ok) {
            const task = tasksData.find(t => t.id === taskId);
            if (task) {
                task.status = 'completed';
                task.actual_deadline = new Date().toISOString();
            }
            renderCalendar();
            if (selectedDate) openPanel(selectedDate);
        }
    });
}

function deleteTask(taskId) {
    if (!confirm('Удалить задачу?')) return;
    fetch(`/task/${taskId}/delete/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
    }).then(() => location.reload());
}

// ── Старт ─────────────────────────────────────────────────────────────────────
renderCalendar();
