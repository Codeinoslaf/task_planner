from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0003_remove_task_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='detected_context',
            field=models.CharField(
                choices=[
                    ('study', 'Учеба'),
                    ('devops', 'DevOps'),
                    ('internship', 'Стажировка'),
                    ('household', 'Бытовые дела'),
                    ('communication', 'Коммуникации'),
                    ('health', 'Здоровье'),
                    ('general', 'Общее'),
                ],
                default='general',
                max_length=30,
                verbose_name='Автоматически распознанный контекст',
            ),
        ),
        migrations.AddField(
            model_name='task',
            name='estimated_minutes',
            field=models.PositiveIntegerField(default=60, verbose_name='Оценка длительности задачи в минутах'),
        ),
        migrations.AddField(
            model_name='task',
            name='difficulty',
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text='Значение от 1 до 5, рассчитывается автоматически по тексту задачи',
                verbose_name='Оценка сложности задачи',
            ),
        ),
        migrations.AddField(
            model_name='task',
            name='profile_confidence',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Уверенность автоматического распознавания'),
        ),
    ]
