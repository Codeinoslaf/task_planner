from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.timezone import localtime, make_aware, now
from django.db.models import Avg, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import datetime as datetime_cls, time as time_cls, timedelta as dt_timedelta
import json
import re
from .models import Task, TaskExecutionStats
from django.contrib.auth import login
from .forms import RegisterForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('calendar')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('calendar')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def calendar_view(request):
    user = request.user
    today = now()

    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        planned_deadline = request.POST.get('planned_deadline')
        task_profile = _infer_task_profile(title, description)

        if task_id:
            task = get_object_or_404(Task, id=task_id, user=user)
            task.title = title
            task.description = description
            task.planned_deadline = planned_deadline
            task.detected_context = task_profile['detected_context']
            task.estimated_minutes = task_profile['estimated_minutes']
            task.difficulty = task_profile['difficulty']
            task.profile_confidence = task_profile['profile_confidence']
            task.save()
        else:
            Task.objects.create(
                user=user,
                title=title,
                description=description,
                planned_deadline=planned_deadline,
                detected_context=task_profile['detected_context'],
                estimated_minutes=task_profile['estimated_minutes'],
                difficulty=task_profile['difficulty'],
                profile_confidence=task_profile['profile_confidence'],
            )

        return redirect('calendar')

    tasks = Task.objects.filter(user=user).order_by('planned_deadline')

    tasks_json = json.dumps([{
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'planned_deadline': task.planned_deadline.isoformat(),
        'actual_deadline': task.actual_deadline.isoformat() if task.actual_deadline else None,
        'status': task.status,
        'created_at': task.created_at.isoformat(),
        'detected_context': task.detected_context,
        'estimated_minutes': task.estimated_minutes,
        'difficulty': task.difficulty,
        'profile_confidence': task.profile_confidence,
    } for task in tasks])

    return render(request, 'tasks/calendar.html', {
        'tasks': tasks,
        'tasks_json': tasks_json,
        'year': today.year,
        'month': today.month,
    })


_DAY_NAMES_RU = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']

_DURATION_GROUPS = {
    'short': {
        'name': 'Короткие задачи',
        'description': 'до 1 дня',
        'icon': '⚡',
    },
    'medium': {
        'name': 'Средние задачи',
        'description': 'от 2 до 7 дней',
        'icon': '📅',
    },
    'long': {
        'name': 'Большие задачи',
        'description': 'больше недели',
        'icon': '🏔️',
    },
}

_TIME_SLOTS = {
    'morning': {'name': 'Утро', 'description': '06:00-12:00', 'icon': '🌅'},
    'day': {'name': 'День', 'description': '12:00-18:00', 'icon': '☀️'},
    'evening': {'name': 'Вечер', 'description': '18:00-23:00', 'icon': '🌙'},
    'night': {'name': 'Ночь', 'description': '23:00-06:00', 'icon': '🌌'},
}

_CONTEXT_META = {
    'study': {
        'label': 'Учеба',
        'keywords': [
            'универ', 'университет', 'учеб', 'экзамен', 'зачет', 'лаба', 'лаборатор',
            'курсов', 'диплом', 'реферат', 'семинар', 'лекци', 'презентац',
            'отчет по практике', 'практик', 'конспект', 'законспектировать',
            'прочитать', 'выучить', 'повторить', 'решить', 'сдать', 'оформить',
            'домаш', 'дз', 'контрольн', 'билеты', 'пара', 'предмет', 'методич',
            'список литературы', 'научрук', 'глава', 'защита',
        ],
    },
    'devops': {
        'label': 'DevOps',
        'keywords': [
            'devops', 'docker', 'kubernetes', 'k8s', 'ci/cd', 'cicd', 'pipeline',
            'deploy', 'деплой', 'сервер', 'linux', 'nginx', 'ansible', 'terraform',
            'мониторинг', 'prometheus', 'grafana', 'helm', 'gitlab', 'compose',
            'dockerfile', 'контейнер', 'образ', 'registry', 'runner', 'workflow',
            'ssh', 'bash', 'скрипт', 'yaml', 'yml', 'postgres', 'postgresql',
            'backup', 'бэкап', 'cron', 'логи', 'логов', 'алерт', 'alert', 'ingress',
            'namespace', 'secret', 'env', 'переменные окружения',
        ],
    },
    'internship': {
        'label': 'Стажировка',
        'keywords': [
            'стажиров', 'ментор', 'ревью', 'джира', 'jira', 'таск', 'тикет',
            'pull request', 'merge request', 'pr ', 'mr ', 'созвон по работе',
            'работа', 'рабоч', 'команда', 'стенд', 'задача от ментора',
            'README', 'readme', 'документац', 'демо', 'статус',
        ],
    },
    'household': {
        'label': 'Быт',
        'keywords': [
            'купить', 'магазин', 'продукт', 'уборк', 'убраться', 'оплатить',
            'квартира', 'документ', 'забрать', 'заказать', 'посылк',
            'еда', 'хлеб', 'молоко', 'овощ', 'фрукты', 'аптека', 'банк',
            'квитанц', 'телефон', 'интернет', 'коммунал', 'стирк', 'постирать',
            'помыть', 'приготовить', 'готовк', 'мусор', 'вынести', 'починить',
            'распечатать', 'справк', 'деканат', 'библиотек', 'книга', 'пункт выдачи',
        ],
    },
    'communication': {
        'label': 'Коммуникации',
        'keywords': [
            'позвонить', 'созвон', 'ответить', 'написать сообщение', 'встреч',
            'обсудить', 'отправить письмо', 'почта',
            'написать в чат', 'договориться', 'уточнить у', 'напомнить',
            'пригласить', 'сообщить',
        ],
    },
    'health': {
        'label': 'Здоровье',
        'keywords': [
            'врач', 'трениров', 'зал', 'аптека', 'лекарств', 'сон', 'отдых',
            'анализы', 'стоматолог', 'поликлиник', 'записаться к врачу',
            'зарядк', 'прогулк',
        ],
    },
}

_EFFORT_RULES = [
    (240, 5, ['диплом', 'курсов', 'проект', 'исследов', 'архитектур', 'kubernetes', 'terraform', 'глава']),
    (180, 4, ['настроить', 'реализовать', 'разобраться', 'ci/cd', 'pipeline', 'deploy', 'сервер', 'backup', 'бэкап']),
    (120, 3, ['подготовить', 'презентац', 'отчет', 'написать', 'изучить', 'доклад', 'оформить', 'выучить']),
    (90, 3, ['лаба', 'лаборатор', 'практик', 'ревью', 'тикет', 'прочитать', 'решить']),
    (45, 2, ['убраться', 'уборк', 'постирать', 'помыть', 'приготовить', 'разобрать документы']),
    (30, 1, ['купить', 'оплатить', 'позвонить', 'отправить', 'ответить', 'забрать', 'заказать', 'распечатать']),
    (15, 1, ['проверить', 'посмотреть', 'уточнить', 'напомнить', 'сообщить']),
]


def _parse_deadline(value):
    if not value:
        return None
    try:
        parsed = datetime_cls.fromisoformat(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime_cls.combine(datetime_cls.strptime(value, '%Y-%m-%d').date(), time_cls.min)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        return make_aware(parsed)
    return parsed


def _normalize_task_text(*parts):
    text = ' '.join(part or '' for part in parts).lower().replace('ё', 'е')
    return re.sub(r'\s+', ' ', text).strip()


def _keyword_hits(text, keywords):
    return [keyword for keyword in keywords if keyword in text]


def _format_minutes(minutes):
    if minutes < 60:
        return f'~{minutes} мин'
    hours = minutes / 60
    if hours.is_integer():
        return f'~{int(hours)} ч'
    return f'~{hours:.1f} ч'


def _difficulty_label(value):
    if value <= 1:
        return 'легкая'
    if value == 2:
        return 'обычная'
    if value == 3:
        return 'средняя'
    if value == 4:
        return 'сложная'
    return 'очень сложная'


def _infer_task_profile(title, description=''):
    text = _normalize_task_text(title, description)
    context_scores = {}
    matched_keywords = []

    for key, meta in _CONTEXT_META.items():
        hits = _keyword_hits(text, meta['keywords'])
        if hits:
            context_scores[key] = len(hits)
            matched_keywords.extend(hits[:2])

    detected_context = 'general'
    if context_scores:
        context_priority = {
            'devops': 6,
            'health': 5,
            'study': 4,
            'internship': 4,
            'household': 3,
            'communication': 2,
            'general': 1,
        }
        detected_context = max(
            context_scores,
            key=lambda key: (context_scores[key], context_priority.get(key, 0)),
        )

    estimated_minutes = 60
    difficulty = 2
    effort_hits = []
    for minutes, rule_difficulty, keywords in _EFFORT_RULES:
        hits = _keyword_hits(text, keywords)
        if hits:
            estimated_minutes = minutes
            difficulty = rule_difficulty
            effort_hits = hits[:2]
            break

    if detected_context == 'devops' and estimated_minutes < 120:
        estimated_minutes = 180
        difficulty = max(difficulty, 4)
    elif detected_context == 'study' and estimated_minutes < 90:
        estimated_minutes = 90
        difficulty = max(difficulty, 3)

    confidence = 25
    if context_scores:
        confidence += min(45, max(context_scores.values()) * 18)
    if effort_hits:
        confidence += 25
    if len(text) > 25:
        confidence += 5

    context_label = _CONTEXT_META.get(detected_context, {'label': 'Общее'})['label']
    return {
        'detected_context': detected_context,
        'context_label': context_label,
        'estimated_minutes': estimated_minutes,
        'estimated_label': _format_minutes(estimated_minutes),
        'difficulty': max(1, min(5, difficulty)),
        'difficulty_label': _difficulty_label(difficulty),
        'profile_confidence': max(0, min(100, confidence)),
        'matched_keywords': list(dict.fromkeys(matched_keywords + effort_hits))[:4],
    }


def _duration_days(created_at, planned_deadline):
    created = localtime(created_at)
    planned = localtime(planned_deadline)
    seconds = max(0, (planned - created).total_seconds())
    return seconds / 86400


def _duration_group(created_at, planned_deadline):
    days = _duration_days(created_at, planned_deadline)
    if days <= 1:
        return 'short'
    if days <= 7:
        return 'medium'
    return 'long'


def _time_slot(deadline):
    hour = localtime(deadline).hour
    if 6 <= hour < 12:
        return 'morning'
    if 12 <= hour < 18:
        return 'day'
    if 18 <= hour < 23:
        return 'evening'
    return 'night'


def _stats_for_group(stats):
    stats = list(stats)
    total = len(stats)
    completed = sum(1 for stat in stats if stat.task.status == 'completed')
    overdue = sum(1 for stat in stats if stat.delay_days > 0)
    avg_delay = sum(stat.delay_days for stat in stats) / total if total else 0
    on_time_rate = ((total - overdue) / total * 100) if total else 0
    return {
        'total': total,
        'completed': completed,
        'overdue': overdue,
        'avg_delay': round(avg_delay, 1),
        'on_time_rate': round(on_time_rate, 1),
    }


@login_required
def profile_view(request):
    user = request.user

    total_tasks = Task.objects.filter(user=user).count()
    completed_tasks = Task.objects.filter(user=user, status='completed').count()
    overdue_tasks = Task.objects.filter(user=user, status='overdue').count()
    active_tasks = Task.objects.filter(user=user).exclude(
        Q(status='completed') | Q(status='overdue')
    ).count()

    avg_delay = TaskExecutionStats.objects.filter(user=user).aggregate(
        Avg('delay_days')
    )['delay_days__avg'] or 0

    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks else 0

    # Процент выполнения в срок (delay_days <= 0)
    on_time_count = TaskExecutionStats.objects.filter(user=user, delay_days__lte=0).count()
    on_time_rate = (on_time_count / completed_tasks * 100) if completed_tasks else 0

    # Самый продуктивный день недели (больше всего вовремя завершённых задач)
    day_counts = {}
    for stat in TaskExecutionStats.objects.filter(user=user, delay_days__lte=0):
        day = stat.actual_deadline.weekday()  # Mon=0, Sun=6
        day_counts[day] = day_counts.get(day, 0) + 1

    productive_day = None
    if day_counts:
        best_day = max(day_counts, key=day_counts.get)
        productive_day = _DAY_NAMES_RU[best_day]

    all_stats = list(TaskExecutionStats.objects.filter(user=user).order_by('created_at'))

    # Автоматическая разбивка по горизонту планирования
    planning_groups = []
    for key, meta in _DURATION_GROUPS.items():
        group_stats = [
            stat for stat in all_stats
            if _duration_group(stat.task.created_at, stat.planned_deadline) == key
        ]
        stat_data = _stats_for_group(group_stats)
        planning_groups.append({
            'key': key,
            'name': meta['name'],
            'description': meta['description'],
            'icon': meta['icon'],
            **stat_data,
        })

    # Аналитика по времени дедлайна
    time_slots = []
    for key, meta in _TIME_SLOTS.items():
        slot_stats = [
            stat for stat in all_stats
            if _time_slot(stat.planned_deadline) == key
        ]
        stat_data = _stats_for_group(slot_stats)
        time_slots.append({
            'key': key,
            'name': meta['name'],
            'description': meta['description'],
            'icon': meta['icon'],
            **stat_data,
        })

    best_time_slot = None
    filled_slots = [slot for slot in time_slots if slot['total'] > 0]
    if filled_slots:
        best_time_slot = max(filled_slots, key=lambda x: (x['on_time_rate'], x['total']))

    context_groups = []
    context_labels = dict(Task.CONTEXT_CHOICES)
    for key, label in context_labels.items():
        context_stat_items = [
            stat for stat in all_stats
            if stat.task.detected_context == key
        ]
        if not context_stat_items:
            continue
        stat_data = _stats_for_group(context_stat_items)
        context_groups.append({
            'key': key,
            'name': label,
            **stat_data,
        })
    context_groups.sort(key=lambda item: (item['total'], item['on_time_rate']), reverse=True)

    riskiest_context = None
    risky_contexts = [item for item in context_groups if item['total'] >= 2]
    if risky_contexts:
        riskiest_context = min(risky_contexts, key=lambda item: (item['on_time_rate'], -item['avg_delay']))

    # Тренд точности планирования
    accuracy_trend = None
    if len(all_stats) >= 4:
        mid = len(all_stats) // 2
        first_avg = sum(s.delay_days for s in all_stats[:mid]) / mid
        second_avg = sum(s.delay_days for s in all_stats[mid:]) / (len(all_stats) - mid)
        if second_avg < first_avg - 0.5:
            accuracy_trend = 'improving'
        elif second_avg > first_avg + 0.5:
            accuracy_trend = 'declining'
        else:
            accuracy_trend = 'stable'

    # Данные для графика: последние 10 завершённых задач
    chart_stats = (
        TaskExecutionStats.objects
        .filter(user=user)
        .select_related('task')
        .order_by('-created_at')[:10]
    )
    chart_data = []
    for stat in chart_stats:
        planned_days = max(1, (stat.planned_deadline - stat.task.created_at).days)
        title = stat.task.title
        chart_data.append({
            'title': title[:18] + ('…' if len(title) > 18 else ''),
            'planned': planned_days,
            'delay': stat.delay_days,
        })
    chart_data.reverse()

    return render(request, 'tasks/profile.html', {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'active_tasks': active_tasks,
        'avg_delay': round(avg_delay, 2),
        'completion_rate': round(completion_rate, 1),
        'on_time_rate': round(on_time_rate, 1),
        'productive_day': productive_day,
        'planning_groups': planning_groups,
        'time_slots': time_slots,
        'best_time_slot': best_time_slot,
        'context_groups': context_groups,
        'riskiest_context': riskiest_context,
        'accuracy_trend': accuracy_trend,
        'chart_data': json.dumps(chart_data),
        'status_chart_data': json.dumps({
            'completed': completed_tasks,
            'overdue': overdue_tasks,
            'active': active_tasks,
        }),
    })


@login_required
def task_list_view(request):
    user = request.user
    filter_type = request.GET.get('filter', 'all')

    tasks_query = Task.objects.filter(user=user)

    if filter_type == 'completed':
        tasks = tasks_query.filter(status='completed').order_by('-actual_deadline')
        page_title = 'Выполненные задачи'
        page_subtitle = 'Все завершенные задачи'
    elif filter_type == 'overdue':
        tasks = tasks_query.filter(status='overdue').order_by('planned_deadline')
        page_title = 'Просроченные задачи'
        page_subtitle = 'Задачи, требующие внимания'
    elif filter_type == 'active':
        tasks = tasks_query.exclude(
            Q(status='completed') | Q(status='overdue')
        ).order_by('planned_deadline')
        page_title = 'Активные задачи'
        page_subtitle = 'Задачи в работе'
    else:
        tasks = tasks_query.order_by('planned_deadline')
        page_title = 'Все задачи'
        page_subtitle = 'Полный список ваших задач'

    total_count = tasks_query.count()
    completed_count = tasks_query.filter(status='completed').count()
    overdue_count = tasks_query.filter(status='overdue').count()
    active_count = tasks_query.exclude(
        Q(status='completed') | Q(status='overdue')
    ).count()

    return render(request, 'tasks/task_list.html', {
        'tasks': tasks,
        'page_title': page_title,
        'page_subtitle': page_subtitle,
        'current_filter': filter_type,
        'total_count': total_count,
        'completed_count': completed_count,
        'overdue_count': overdue_count,
        'active_count': active_count,
    })


@login_required
def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)

    if request.method == 'POST' and task.status != 'completed':
        task.actual_deadline = now()
        task.status = 'completed'
        task.save()

        delay_days = (task.actual_deadline.date() - task.planned_deadline.date()).days

        TaskExecutionStats.objects.create(
            user=request.user,
            task=task,
            planned_deadline=task.planned_deadline,
            actual_deadline=task.actual_deadline,
            delay_days=delay_days
        )

    referer = request.META.get('HTTP_REFERER', '')
    if 'task-list' in referer:
        return redirect('task_list')
    return redirect('calendar')


@login_required
@require_POST
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    referer = request.META.get('HTTP_REFERER', '')
    if 'task-list' in referer:
        return redirect('task_list')
    return redirect('calendar')


@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)

    if request.method == 'POST':
        task.title = request.POST.get('title')
        task.description = request.POST.get('description', '')
        task.planned_deadline = request.POST.get('planned_deadline')
        task_profile = _infer_task_profile(task.title, task.description)
        task.detected_context = task_profile['detected_context']
        task.estimated_minutes = task_profile['estimated_minutes']
        task.difficulty = task_profile['difficulty']
        task.profile_confidence = task_profile['profile_confidence']
        task.save()
        return redirect('calendar')

    return JsonResponse({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'planned_deadline': task.planned_deadline.isoformat(),
        'detected_context': task.detected_context,
        'estimated_minutes': task.estimated_minutes,
        'difficulty': task.difficulty,
        'profile_confidence': task.profile_confidence,
    })


@login_required
def ai_hint(request):
    planned_deadline = _parse_deadline(
        request.GET.get('planned_deadline') or request.GET.get('planned_date', '')
    )
    if not planned_deadline:
        return JsonResponse({'no_data': True})

    title = request.GET.get('title', '')
    description = request.GET.get('description', '')
    current_task_id = request.GET.get('task_id')
    task_profile = _infer_task_profile(title, description)
    has_task_text = bool((title or description).strip())
    now_time = localtime(now())
    selected_date = localtime(planned_deadline).date()
    duration_group = _duration_group(now_time, planned_deadline)
    time_slot = _time_slot(planned_deadline)
    all_stats = list(
        TaskExecutionStats.objects
        .filter(user=request.user)
        .select_related('task')
    )
    stats = [
        stat for stat in all_stats
        if _duration_group(stat.task.created_at, stat.planned_deadline) == duration_group
    ]
    context_stats = [
        stat for stat in all_stats
        if has_task_text and stat.task.detected_context == task_profile['detected_context']
    ]
    analysis_stats = context_stats if len(context_stats) >= 3 else stats

    cards = []
    total = len(analysis_stats)
    overdue_count = 0
    avg_delay_val = 0
    avg_planned = 0
    on_time_rate = 0
    risk_reasons = []
    days_until = max(0, (localtime(planned_deadline) - now_time).total_seconds() / 86400)

    day_tasks_query = Task.objects.filter(
        user=request.user,
        status='planned',
        planned_deadline__date=selected_date,
    )
    if current_task_id:
        day_tasks_query = day_tasks_query.exclude(id=current_task_id)
    day_tasks = day_tasks_query.count()
    day_effort_minutes = (
        sum((task.estimated_minutes or 60) for task in day_tasks_query)
        + (task_profile['estimated_minutes'] if has_task_text else 0)
    )
    is_light_task = (
        has_task_text
        and task_profile['estimated_minutes'] <= 45
        and task_profile['difficulty'] <= 1
    )

    slot_stats = [stat for stat in analysis_stats if _time_slot(stat.planned_deadline) == time_slot]
    selected_slot_data = _stats_for_group(slot_stats) if len(slot_stats) >= 2 else None

    all_slot_results = []
    for key, meta in _TIME_SLOTS.items():
        current = [stat for stat in all_stats if _time_slot(stat.planned_deadline) == key]
        if current:
            all_slot_results.append({
                'key': key,
                'name': meta['name'],
                **_stats_for_group(current),
            })

    best_slot = None
    if all_slot_results:
        best_slot = max(all_slot_results, key=lambda x: (x['on_time_rate'], x['total']))

    result = {
        'total': total,
        'duration_group': duration_group,
        'duration_group_name': _DURATION_GROUPS[duration_group]['name'],
        'time_slot': time_slot,
        'time_slot_name': _TIME_SLOTS[time_slot]['name'],
        'assessment_mode': 'task_risk' if has_task_text else 'day_context',
        'task_profile': {
            'context': task_profile['detected_context'],
            'context_label': task_profile['context_label'],
            'estimated_minutes': task_profile['estimated_minutes'],
            'estimated_label': task_profile['estimated_label'],
            'difficulty': task_profile['difficulty'],
            'difficulty_label': task_profile['difficulty_label'],
            'confidence': task_profile['profile_confidence'],
            'matched_keywords': task_profile['matched_keywords'],
            'has_text': has_task_text,
        },
    }

    if analysis_stats:
        overdue_count = sum(1 for stat in analysis_stats if stat.delay_days > 0)
        avg_delay_val = sum(stat.delay_days for stat in analysis_stats) / total
        planned_durations = [
            _duration_days(stat.task.created_at, stat.planned_deadline)
            for stat in analysis_stats
            if _duration_days(stat.task.created_at, stat.planned_deadline) > 0
        ]
        avg_planned = sum(planned_durations) / len(planned_durations) if planned_durations else 0
        on_time_rate = round((total - overdue_count) / total * 100, 1) if total else 0

        result.update({
            'avg_planned': round(avg_planned, 1),
            'avg_delay': round(avg_delay_val, 1),
        })

    history_risk = 0 if not has_task_text else 45
    if has_task_text and analysis_stats:
        history_risk = max(0, min(55, (100 - on_time_rate) * 0.45 + max(0, avg_delay_val) * 8))
        if on_time_rate < 50:
            risk_reasons.append('похожие задачи часто закрывались позже дедлайна')
        elif avg_delay_val > 0:
            risk_reasons.append('по похожим задачам уже было среднее опоздание')
    elif has_task_text:
        risk_reasons.append('пока мало истории для точного прогноза')

    pace_risk = 0
    if has_task_text and analysis_stats and avg_planned > 0 and not is_light_task:
        ratio = days_until / avg_planned
        if ratio < 0.5:
            pace_risk = 25
            risk_reasons.append('заложено заметно меньше времени, чем обычно нужно')
        elif ratio < 0.85:
            pace_risk = 15
            risk_reasons.append('срок чуть плотнее обычного темпа')

    load_risk = min(16, day_tasks * 5)
    if day_tasks >= 3:
        risk_reasons.append('на выбранный день уже много дедлайнов')
    elif day_tasks > 0:
        risk_reasons.append('на выбранный день уже есть задачи')

    effort_risk = 0
    if day_effort_minutes > 300:
        effort_risk = 22
        risk_reasons.append('по оценке времени день перегружен' if has_task_text else 'выбранный день уже перегружен')
    elif day_effort_minutes > 210:
        effort_risk = 12
        risk_reasons.append('суммарная нагрузка дня близка к пределу')

    difficulty_risk = max(0, (task_profile['difficulty'] - 2) * 6) if has_task_text else 0
    if has_task_text and task_profile['difficulty'] >= 4 and task_profile['profile_confidence'] >= 50:
        risk_reasons.append('по тексту задача выглядит сложной')

    context_risk = 0
    context_data = _stats_for_group(context_stats) if len(context_stats) >= 2 else None
    if has_task_text and context_data:
        context_risk = max(0, min(16, (100 - context_data['on_time_rate']) * 0.14 + max(0, context_data['avg_delay']) * 4))
        if context_data['on_time_rate'] < 60:
            risk_reasons.append('в похожем контексте дедлайны часто срывались')

    weekend_sensitive_contexts = {'study', 'devops', 'internship', 'general'}
    weekend_risk = 8 if (
        localtime(planned_deadline).weekday() >= 5
        and (not has_task_text or task_profile['detected_context'] in weekend_sensitive_contexts)
    ) else 0
    if weekend_risk:
        risk_reasons.append('дедлайн стоит на выходной')

    slot_risk = 0
    if selected_slot_data:
        slot_risk = max(0, min(15, (100 - selected_slot_data['on_time_rate']) * 0.15))
        if selected_slot_data['on_time_rate'] < 60:
            risk_reasons.append('в это время суток задачи чаще срывались')

    overdue_active = Task.objects.filter(
        user=request.user,
        status='planned',
        planned_deadline__lt=now_time,
    ).count()
    backlog_risk = min(12, overdue_active * 6)
    if overdue_active:
        risk_reasons.append('есть активные задачи с прошедшим сроком')

    risk_score = round(min(
        100,
        history_risk + pace_risk + load_risk + effort_risk + difficulty_risk
        + context_risk + weekend_risk + slot_risk + backlog_risk
    ))
    if risk_score >= 70:
        risk_level = 'high'
        risk_title = 'Высокий риск срыва' if has_task_text else 'День перегружен'
        risk_text = (
            'Этот дедлайн лучше пересмотреть: система видит несколько факторов риска.'
            if has_task_text
            else 'На выбранную дату уже много нагрузки. Добавьте название задачи, чтобы оценить ее точнее.'
        )
    elif risk_score >= 40:
        risk_level = 'medium'
        risk_title = 'Средний риск' if has_task_text else 'День стоит проверить'
        risk_text = (
            'Дедлайн возможен, но его стоит проверить по нагрузке и истории.'
            if has_task_text
            else 'Дата выглядит возможной, но итоговый риск станет понятен после названия задачи.'
        )
    else:
        risk_level = 'low'
        risk_title = 'Низкий риск' if has_task_text else 'День выглядит свободно'
        risk_text = (
            'По истории и текущей нагрузке дедлайн выглядит реалистично.'
            if has_task_text
            else 'Пока оценивается только выбранная дата. Введите название задачи, чтобы система распознала сложность.'
        )

    result.update({
        'risk_score': risk_score,
        'risk_level': risk_level,
        'risk_title': risk_title,
        'risk_text': risk_text,
        'risk_reasons': risk_reasons[:3],
        'day_tasks': day_tasks,
        'day_effort_minutes': day_effort_minutes,
    })

    if not has_task_text:
        cards.append({
            'kind': 'day',
            'level': risk_level,
            'title': 'Добавьте название задачи',
            'text': 'После ввода названия система определит контекст, примерную длительность и сложность, а затем пересчитает риск дедлайна.',
        })

    if has_task_text and analysis_stats and avg_planned > 0:
        ratio = days_until / avg_planned
        group_name = _DURATION_GROUPS[duration_group]['name'].lower()
        recommended_days = max(avg_planned + max(avg_delay_val, 0), avg_planned)
        suggested_deadline_date = now_time.date() + dt_timedelta(days=max(1, round(recommended_days)))
        should_suggest_date = selected_date < suggested_deadline_date
        suggested_deadline_text = suggested_deadline_date.strftime('%d.%m')
        if is_light_task and on_time_rate >= 70:
            risk = 'low'
            title = 'Для этой задачи срок выглядит спокойно'
            text = (
                f'Похожие бытовые задачи выполнялись вовремя в {on_time_rate}% случаев. '
                f'Выбранная дата подходит.'
            )
        elif ratio < 0.5 or ((avg_delay_val > 2 or on_time_rate < 40) and should_suggest_date):
            risk = 'high'
            title = 'Дедлайн может сорваться'
            if should_suggest_date:
                text = (
                    f'Это похоже на {group_name}: обычно они занимают около {round(avg_planned, 1)} дн., '
                    f'а сейчас заложено {round(days_until, 1)} дн. Реалистичнее поставить {suggested_deadline_text}.'
                )
            else:
                text = (
                    f'История похожих задач рискованная: среднее отклонение {round(avg_delay_val, 1)} дн. '
                    f'Но по дате уже есть запас, лучше уточнить объем задачи или добавить резерв.'
                )
        elif ratio < 0.85 or ((avg_delay_val > 0 or on_time_rate < 70) and should_suggest_date):
            risk = 'medium'
            title = 'Срок лучше смягчить'
            if should_suggest_date:
                text = (
                    f'Для похожих задач среднее отклонение {round(avg_delay_val, 1)} дн.; '
                    f'вовремя получается в {on_time_rate}% случаев. Спокойнее перенести на {suggested_deadline_text}.'
                )
            else:
                text = (
                    f'Для похожих задач среднее отклонение {round(avg_delay_val, 1)} дн., '
                    f'но выбранная дата уже не раньше рекомендуемой.'
                )
        elif on_time_rate < 70:
            risk = 'medium'
            title = 'История похожих задач неоднозначная'
            text = (
                f'Вовремя получалось в {on_time_rate}% случаев. По дате запас есть, '
                f'но задачу лучше держать под контролем.'
            )
        else:
            risk = 'low'
            title = 'Срок выглядит реалистично'
            text = (
                f'Похожие задачи выполнялись вовремя в {on_time_rate}% случаев. '
                f'Выбранная дата выглядит нормально.'
            )

        card = {
            'kind': 'deadline',
            'level': risk,
            'title': title,
            'text': text,
        }
        if risk in ('high', 'medium') and should_suggest_date:
            card['suggested_date'] = suggested_deadline_date.isoformat()
            card['action_text'] = f'Перенести на {suggested_deadline_text}'
        cards.append(card)

    elif has_task_text and not analysis_stats:
        cards.append({
            'kind': 'deadline',
            'level': 'medium',
            'title': 'Пока мало истории',
            'text': 'Для такого горизонта планирования еще нет завершенных задач, поэтому оценка будет уточняться со временем.',
        })

    if weekend_risk:
        cards.append({
            'kind': 'day',
            'level': 'medium',
            'title': 'Дедлайн на выходной',
            'text': 'Если задача зависит от учебы или стажировки, будний день может быть удобнее.',
        })

    if day_tasks > 0:
        level = 'high' if day_tasks >= 3 else 'medium'
        day_card = {
            'kind': 'day_load',
            'level': level,
            'title': 'День уже загружен',
            'text': f'На эту дату уже запланировано дедлайнов: {day_tasks}.',
        }
        best_date = None
        best_count = day_tasks
        for offset in range(1, 8):
            candidate = selected_date + dt_timedelta(days=offset)
            candidate_count = Task.objects.filter(
                user=request.user,
                status='planned',
                planned_deadline__date=candidate,
            ).count()
            if candidate_count < best_count:
                best_date = candidate
                best_count = candidate_count
                if candidate_count == 0:
                    break
        if best_date:
            day_card['suggested_date'] = best_date.isoformat()
            day_card['action_text'] = f'Свободнее: {best_date.strftime("%d.%m")}'
        cards.append(day_card)

    if best_slot:
        current_rate = selected_slot_data['on_time_rate'] if selected_slot_data else None
        if best_slot['key'] != time_slot and best_slot['total'] >= 2:
            if current_rate is None or best_slot['on_time_rate'] >= current_rate + 10:
                cards.append({
                    'kind': 'time_slot',
                    'level': 'medium',
                    'title': 'Есть более удачное время',
                    'text': (
                        f'По истории самый успешный период: {best_slot["name"]} '
                        f'({best_slot["on_time_rate"]}% вовремя).'
                    ),
                    'suggested_time': {
                        'morning': '09:00',
                        'day': '14:00',
                        'evening': '18:00',
                        'night': '22:00',
                    }[best_slot['key']],
                    'action_text': f'Попробовать {best_slot["name"].lower()}',
                })

    result['cards'] = cards[:3]

    return JsonResponse(result)


@login_required
def notifications_view(request):
    user = request.user
    now_time = localtime(now())
    today = now_time.date()

    due_today = Task.objects.filter(
        user=user,
        status='planned',
        planned_deadline__date=today,
    ).order_by('planned_deadline')

    one_hour_before = Task.objects.filter(
        user=user,
        status='planned',
        planned_deadline__gte=now_time,
        planned_deadline__lte=now_time + dt_timedelta(hours=1),
    ).order_by('planned_deadline')

    notifs = []

    for task in due_today:
        deadline = localtime(task.planned_deadline)
        notifs.append({
            'id': f'{task.id}:due_today',
            'task_id': task.id,
            'type': 'due_today',
            'title': task.title,
            'message': f'Дедлайн сегодня в {deadline.strftime("%H:%M")}',
            'time_left': 'сегодня',
            'deadline': deadline.isoformat(),
            'urgency': 'high',
        })

    for task in one_hour_before:
        deadline = localtime(task.planned_deadline)
        delta = deadline - now_time
        secs = int(delta.total_seconds())

        if secs < 60:
            time_str = 'менее минуты'
        elif secs < 3600:
            time_str = f'{max(1, secs // 60)} мин.'
        else:
            time_str = '1 ч.'

        notifs.append({
            'id': f'{task.id}:one_hour_before',
            'task_id': task.id,
            'type': 'one_hour_before',
            'title': task.title,
            'message': f'До дедлайна осталось {time_str}',
            'time_left': time_str,
            'deadline': deadline.isoformat(),
            'urgency': 'critical',
        })

    return JsonResponse({'notifications': notifs, 'count': len(notifs)})
