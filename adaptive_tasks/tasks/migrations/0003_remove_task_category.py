from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0002_task_category'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='task',
            name='category',
        ),
    ]
