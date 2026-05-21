from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='category',
            field=models.CharField(
                choices=[
                    ('work', 'Работа'),
                    ('study', 'Учёба'),
                    ('personal', 'Личное'),
                    ('health', 'Здоровье'),
                    ('finance', 'Финансы'),
                    ('other', 'Другое'),
                ],
                default='other',
                max_length=20,
                verbose_name='Категория',
            ),
        ),
    ]
