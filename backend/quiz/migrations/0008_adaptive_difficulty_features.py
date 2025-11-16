from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0007_anonymous_user_tracking'),
    ]

    operations = [
        migrations.AddField(
            model_name='tempexamquestion',
            name='is_adaptive',
            field=models.BooleanField(default=False, help_text='Bu soru adaptif zorluk sistemi tarafından seçildi mi?'),
        ),
        migrations.AddField(
            model_name='tempexamquestion',
            name='target_difficulty',
            field=models.PositiveSmallIntegerField(default=3, help_text='Hedeflenen zorluk seviyesi (1-5)'),
        ),
        migrations.AddField(
            model_name='tempexamquestion',
            name='difficulty_confidence',
            field=models.FloatField(default=0.5, help_text='Zorluk seviyesi güven oranı (0-1)'),
        ),
        migrations.AddField(
            model_name='tempexamquestion',
            name='adaptation_reason',
            field=models.CharField(max_length=100, blank=True, null=True, help_text='Bu zorluk seçiminin sebebi'),
        ),
        migrations.AddField(
            model_name='tempexamquestion',
            name='user_performance_prediction',
            field=models.FloatField(blank=True, null=True, help_text='Kullanıcının bu sorudaki beklenen başarı oranı'),
        ),
    ]