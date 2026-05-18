from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class Task(models.Model):

    STATUS_CHOICES = (
        ('planned', 'Запланирована'),
        ('completed', 'Выполнена'),
        ('overdue', 'Просрочена'),
    )

    CONTEXT_CHOICES = (
        ('study', 'Учеба'),
        ('devops', 'DevOps'),
        ('internship', 'Стажировка'),
        ('household', 'Бытовые дела'),
        ('communication', 'Коммуникации'),
        ('health', 'Здоровье'),
        ('general', 'Общее'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255, verbose_name='Название задачи')
    description = models.TextField(blank=True, verbose_name='Описание')
    planned_deadline = models.DateTimeField(verbose_name='Плановый дедлайн')
    actual_deadline = models.DateTimeField(null=True, blank=True, verbose_name='Фактическое завершение')
    detected_context = models.CharField(
        max_length=30,
        choices=CONTEXT_CHOICES,
        default='general',
        verbose_name='Автоматически распознанный контекст',
    )
    estimated_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name='Оценка длительности задачи в минутах',
    )
    difficulty = models.PositiveSmallIntegerField(
        default=2,
        verbose_name='Оценка сложности задачи',
        help_text='Значение от 1 до 5, рассчитывается автоматически по тексту задачи',
    )
    profile_confidence = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Уверенность автоматического распознавания',
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned',
                              verbose_name='Статус')

    created_at = models.DateTimeField(auto_now_add=True,verbose_name='Дата создания')

    def __str__(self):
        return f'{self.title} ({self.user.username})'


class TaskExecutionStats(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_stats')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='execution_stats')
    planned_deadline = models.DateTimeField(verbose_name='Плановый дедлайн')
    actual_deadline = models.DateTimeField(verbose_name='Фактическое завершение')

    delay_days = models.IntegerField(verbose_name='Отклонение от дедлайна (в днях)',
                                     help_text='Отрицательное значение означает досрочное выполнение')

    created_at = models.DateTimeField(auto_now_add=True,verbose_name='Дата записи статистики')

    def __str__(self):
        return f'Статистика задачи "{self.task.title}"'


class UserPerformanceProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='performance_profile')
    avg_delay_days = models.FloatField(default=0.0, verbose_name='Среднее отклонение от дедлайна (дни)')
    completion_rate = models.FloatField(default=0.0, verbose_name='Доля выполненных задач')
    early_completion_rate = models.FloatField(default=0.0, verbose_name='Доля задач, выполненных раньше срока')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='Дата последнего обновления статистики')

    def __str__(self):
        return f'Профиль эффективности {self.user.username}'
