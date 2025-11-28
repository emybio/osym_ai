from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class Subject(models.Model):
    """
    TR, MAT, FIZ, KIM, BIO, GEO vb. dersler.
    """
    code = models.CharField(max_length=5, unique=True)  # Örn: TR, MAT, FIZ
    name = models.CharField(max_length=50)              # Örn: Türkçe, Matematik

    def __str__(self):
        return self.name


class Topic(models.Model):
    """
    Her dersin müfredat konuları. TYT/AYT ayrımı burada yapılır.
    """
    PHASE_CHOICES = [
        ("TYT", "TYT"),
        ("AYT", "AYT"),
        ("BOTH", "Her İkisi"),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    name = models.CharField(max_length=100)
    phase = models.CharField(max_length=4, choices=PHASE_CHOICES)

    def __str__(self):
        return f"{self.subject.name} - {self.name} ({self.phase})"


class Subskill(models.Model):
    """
    Konuya bağlı alt kazanımlar (ör: Noktalama → nokta, virgül, ünlem, konuşma çizgisi...)
    """
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="subskills")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.topic.name} / {self.name}"


class Question(models.Model):
    """
    AI tarafından üretilen veya manuel eklenen soru.
    """
    id = models.CharField(max_length=30, primary_key=True)  # Örn: TR-NOK-004
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, blank=True)
    subskills = models.ManyToManyField(Subskill, blank=True)

    question_text = models.TextField()  # Gövde (şimdilik plain text; ileride HTML/SVG olabilir)
    difficulty = models.PositiveSmallIntegerField(default=3)  # 1–5 ölçeği
    cognitive = models.CharField(max_length=50, default="Kavrama")  # Örn: Bilgi, Kavrama, Analiz

    correct_answer = models.CharField(max_length=1)  # "A", "B", "C", "D", "E"
    explanation = models.TextField(blank=True)  # Rubrik açıklama
    created_at = models.DateTimeField(auto_now_add=True)

    # Duplicate tracking fields
    similarity_score = models.FloatField(null=True, blank=True, help_text="En yüksek benzerlik skoru (0-1 arası)")
    is_duplicate = models.BooleanField(default=False, help_text="Kopya soru olarak işaretlendi mi?")
    duplicate_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='duplicates', help_text="Hangi sorunun kopyası olduğu")
    embedding_vector = models.JSONField(null=True, blank=True, help_text="Vektör gösterimi (gelecek kullanım için)")
    last_similarity_check = models.DateTimeField(null=True, blank=True, help_text="Son benzerlik kontrol tarihi")

    def __str__(self):
        return f"{self.id} - {self.topic.name if self.topic else 'No Topic'}"


class UserQuestionHistory(models.Model):
    """
    Kullanıcıların soru çözüm geçmişini takip etmek için optimize edilmiş model
    Performans için Redis cache ile birlikte çalışır
    """
    user_identifier = models.CharField(max_length=255, db_index=True)  # session_key, IP, user_id etc.
    question = models.ForeignKey(Question, on_delete=models.CASCADE, db_index=True)
    session = models.ForeignKey('TempExamSession', null=True, blank=True, on_delete=models.SET_NULL)
    answered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_correct = models.BooleanField(null=True, blank=True)  # null for unanswered questions
    answer_given = models.CharField(max_length=1, null=True, blank=True)  # A, B, C, D, E
    time_spent_seconds = models.PositiveIntegerField(null=True, blank=True)
    difficulty_rating = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-5 user rating

    class Meta:
        indexes = [
            models.Index(fields=['user_identifier', 'answered_at']),
            models.Index(fields=['user_identifier', 'question']),
            models.Index(fields=['session', 'answered_at']),
        ]
        unique_together = ['user_identifier', 'question']  # Aynı kullanıcı aynı soruyu bir kez görebilir
        ordering = ['-answered_at']

    def __str__(self):
        return f"{self.user_identifier} - {self.question.id} ({self.answered_at})"


class UserPerformanceMetrics(models.Model):
    """
    Kullanıcı performans metrikleri için aggregate model
    Performans optimizasyonu için günlük/haftalık özetler tutar
    """
    user_identifier = models.CharField(max_length=255, db_index=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date = models.DateField(db_index=True)  # Günlük aggregate

    # Performans metrikleri
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    average_time_seconds = models.FloatField(default=0)
    difficulty_distribution = models.JSONField(default=dict)  # {1: count, 2: count, ...}
    topic_performance = models.JSONField(default=dict)  # {topic_name: {correct, total}}

    # Trend metrikleri
    improvement_score = models.FloatField(default=0)  # -1 to 1 scale
    consistency_score = models.FloatField(default=0)  # 0 to 1 scale

    class Meta:
        indexes = [
            models.Index(fields=['user_identifier', 'date']),
            models.Index(fields=['subject', 'date']),
        ]
        unique_together = ['user_identifier', 'subject', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user_identifier} - {self.subject.name} ({self.date})"


class Choice(models.Model):
    """
    Çoktan seçmeli şıklar.
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    label = models.CharField(max_length=1)  # A, B, C, D, E
    text = models.TextField()
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.question.id}-{self.label}"


class Measure(models.Model):
    """
    Sorunun ölçtüğü alt kazanımlar.
    weight değerleri toplamda ≈ 1.0 olacak şekilde ayarlanabilir.
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="measures")
    subskill = models.ForeignKey(Subskill, on_delete=models.CASCADE)
    rule = models.CharField(max_length=200)   # Örn: "Tırnak içinde noktalamanın konumu"
    weight = models.FloatField(default=1.0)

    def __str__(self):
        return f"{self.question.id} - {self.subskill.name}"


class Misconception(models.Model):
    """
    Her yanlış şık için tipik kavram yanılgıları.
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="misconceptions")
    choice_label = models.CharField(max_length=1)  # A/B/C/D/E
    description = models.TextField()

    def __str__(self):
        return f"{self.question.id} - {self.choice_label}"


class StudentResult(models.Model):
    """
    Öğrencinin sınav cevapları ve alt kazanım bazlı sonuçları.
    """
    student_id = models.CharField(max_length=50)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=1)
    is_correct = models.BooleanField(default=False)
    measures_result = models.JSONField(default=dict)  # Örn: {"Tırnak:Aktarılan söz": 0.3}
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_id} - {self.question.id}"


class PastQuestion(models.Model):
    """
    Geçmiş yıllardaki TYT/AYT soruları için yapı.
    Bunlar AI üretiminde 'biçim ve zorluk' referansı olarak kullanılacak.
    """
    year = models.IntegerField()
    exam = models.CharField(max_length=3, choices=[("TYT", "TYT"), ("AYT", "AYT")])
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)

    question_text = models.TextField()
    choices = models.JSONField(default=dict)  # {"A":"...", "B":"...", ...}
    correct_answer = models.CharField(max_length=1)
    cognitive_level = models.CharField(max_length=50)        # Bilgi/Kavrama/Analiz...
    difficulty = models.PositiveSmallIntegerField(default=3) # 1–5

    def __str__(self):
        return f"{self.year} {self.exam} - {self.subject.code} - {self.topic.name}"


class PDFDocument(models.Model):
    """
    Müfredat PDF'leri ve geçmiş soru PDF'leri için doküman modeli.
    Admin panel üzerinden yükleme ve yönetim sağlar.
    """
    DOCUMENT_TYPES = [
        ("CURRICULUM", "Müfredat/Konu Anlatımı"),
        ("PAST_EXAM", "Geçmiş Sınav Soruları"),
    ]

    EXAM_TYPES = [
        ("TYT", "TYT"),
        ("AYT", "AYT"),
        ("BOTH", "Her İkisi"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="pdfs/")
    document_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES)
    exam_type = models.CharField(max_length=4, choices=EXAM_TYPES, blank=True)
    year = models.IntegerField(null=True, blank=True, help_text="Sadece geçmiş sınav PDF'leri için")
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    is_processed = models.BooleanField(default=False, help_text="Embeding işlemi yapıldı mı?")
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document_type', 'exam_type']),
            models.Index(fields=['year']),
            models.Index(fields=['is_processed']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"

    def get_file_size(self):
        """Dosya boyutunu MB cinsinden döner."""
        if self.file:
            return round(self.file.size / (1024 * 1024), 2)
        return 0


class PDFProcessingLog(models.Model):
    """
    PDF işleme loglarını tutar.
    """
    STATUS_CHOICES = [
        ("QUEUED", "Queue'de Bekliyor"),
        ("PROCESSING", "İşleniyor"),
        ("SUCCESS", "Başarılı"),
        ("ERROR", "Hata"),
        ("CLEANUP", "Temizlik"),
    ]

    pdf_document = models.ForeignKey(PDFDocument, on_delete=models.CASCADE, related_name="processing_logs")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    error_details = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.pdf_document.title} - {self.get_status_display()}"


# Hızlı Test modülleri
class TempExamSession(models.Model):
    """
    Kullanıcının kayıtsız çözdüğü hızlı test oturum bilgileri
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    session_key = models.CharField(max_length=64, blank=True, null=True)
    exam_type = models.CharField(max_length=20, choices=[("TYT", "TYT"), ("AYT", "AYT")])
    branch = models.CharField(
        max_length=20,
        choices=[("SAY", "Sayısal"), ("EA", "Eşit Ağırlık"), ("SOZ", "Sözel")]
    )
    question_count = models.IntegerField(default=12)
    duration_minutes = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        default="active",
        choices=[
            ("active", "Aktif"),
            ("completed", "Tamamlandı"),
            ("merged", "Birleştirildi"),
            ("expired", "Süresi Doldu"),
        ]
    )
    temp_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.exam_type} {self.branch} - {self.uuid}"


class TempExamQuestion(models.Model):
    """
    Hızlı test soruları
    """
    session = models.ForeignKey(TempExamSession, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    options = models.JSONField()  # {"A": "...", "B": "...", ...}
    correct_option = models.CharField(max_length=5)
    subject = models.CharField(max_length=50)
    topic = models.CharField(max_length=100, blank=True, null=True)
    difficulty = models.CharField(max_length=20, blank=True, null=True)
    order = models.PositiveIntegerField(default=1)

    # Adaptive Difficulty Fields
    is_adaptive = models.BooleanField(
        default=False,
        help_text='Bu soru adaptif zorluk sistemi tarafından seçildi mi?'
    )
    target_difficulty = models.PositiveSmallIntegerField(
        default=3,
        help_text='Hedeflenen zorluk seviyesi (1-5)'
    )
    difficulty_confidence = models.FloatField(
        default=0.5,
        help_text='Zorluk seviyesi güven oranı (0-1)'
    )
    adaptation_reason = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Bu zorluk seçiminin sebebi'
    )
    user_performance_prediction = models.FloatField(
        blank=True,
        null=True,
        help_text='Kullanıcının bu sorudaki beklenen başarı oranı'
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        adaptive_info = " (Adaptive)" if self.is_adaptive else ""
        return f"{self.session.uuid} - {self.subject}{adaptive_info}"


class TempExamResult(models.Model):
    """
    Hızlı test sonuçları
    """
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(TempExamSession, on_delete=models.CASCADE, related_name="result")
    # anonymous_user = models.ForeignKey('quiz.AnonymousUser', on_delete=models.CASCADE, null=True, blank=True, related_name="temp_results")
    total_questions = models.IntegerField()
    correct_count = models.IntegerField()
    wrong_count = models.IntegerField()
    percentage = models.FloatField()
    subject_breakdown = models.JSONField(default=dict)  # {"Matematik": {"correct": 3, "total": 5}}
    created_at = models.DateTimeField(auto_now_add=True)
    merged = models.BooleanField(default=False)

    def __str__(self):
        return f"Result {self.uuid} - {self.percentage}%"


class ExamResult(models.Model):
    """
    Kullanıcının kalıcı sınav sonuçları
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exam_results")
    source_uuid = models.UUIDField(blank=True, null=True, help_text="TempExamResult uuid'si")
    exam_type = models.CharField(max_length=20, choices=[("TYT", "TYT"), ("AYT", "AYT")])
    branch = models.CharField(
        max_length=20,
        choices=[("SAY", "Sayısal"), ("EA", "Eşit Ağırlık"), ("SOZ", "Sözel")]
    )
    total_questions = models.IntegerField()
    correct_count = models.IntegerField()
    wrong_count = models.IntegerField()
    percentage = models.FloatField()
    subject_breakdown = models.JSONField(default=dict)
    is_quick_test = models.BooleanField(default=False, help_text="Hızlı test mi?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.exam_type} {self.percentage}%"


# Eski modelleri geçiş için koruyalım (ilerde silinebilir)
class Attempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.CharField(max_length=1)
    correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class AnonymousUser(models.Model):
    """
    Cookie ve IP ile takip edilen anonim kullanıcılar
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    browser_id = models.CharField(max_length=255, unique=True, help_text="Tarayıcı cookie'si")
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)

    # Zaman bilgileri
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    # Durum bilgileri
    is_active = models.BooleanField(default=True)

    # Test limitleri
    daily_test_count = models.IntegerField(default=0)
    weekly_test_count = models.IntegerField(default=0)
    total_test_count = models.IntegerField(default=0)
    last_test_date = models.DateTimeField(null=True, blank=True)

    # Block bilgileri
    blocked_until = models.DateTimeField(null=True, blank=True)
    block_reason = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Anonymous User'
        verbose_name_plural = 'Anonymous Users'
        indexes = [
            models.Index(fields=['browser_id']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['last_seen']),
        ]

    def __str__(self):
        return f"Anonymous {self.browser_id[:8]}..."

    def is_blocked(self):
        """Kullanıcının block'lı olup olmadığını kontrol et"""
        if not self.blocked_until:
            return False
        return timezone.now() < self.blocked_until

    def can_take_test(self):
        """Test çözebilir mi kontrol et"""
        # Block kontrolü
        if self.is_blocked():
            return False, f"Blocked until {self.blocked_until}. Reason: {self.block_reason}"

        # Günlük limit kontrolü (5 test)
        today = timezone.now().date()
        today_tests = TempExamResult.objects.filter(
            anonymous_user=self,
            created_at__date=today
        ).count()

        if today_tests >= 5:
            return False, "Daily limit reached (5 tests per day)"

        # Haftalık limit kontrolü (20 test)
        week_ago = timezone.now() - timezone.timedelta(days=7)
        week_tests = TempExamResult.objects.filter(
            anonymous_user=self,
            created_at__gte=week_ago
        ).count()

        if week_tests >= 20:
            return False, "Weekly limit reached (20 tests per week)"

        return True, "Can take test"

    def update_test_count(self):
        """Test sayısını güncelle"""
        now = timezone.now()
        self.last_test_date = now
        self.total_test_count += 1

        # Günlük ve haftalık sayıları hesapla
        today = now.date()
        today_start = timezone.datetime.combine(today, timezone.time.min)
        today_start = timezone.make_aware(today_start)

        self.daily_test_count = TempExamResult.objects.filter(
            anonymous_user=self,
            created_at__gte=today_start
        ).count()

        week_ago = now - timezone.timedelta(days=7)
        self.weekly_test_count = TempExamResult.objects.filter(
            anonymous_user=self,
            created_at__gte=week_ago
        ).count()

        self.save()


class AnonymousStats(models.Model):
    """
    Anonim kullanıcıların istatistikleri
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    anonymous_user = models.ForeignKey(AnonymousUser, on_delete=models.CASCADE, related_name='stats')

    # Test türü bilgileri
    exam_type = models.CharField(max_length=20, choices=[('TYT', 'TYT'), ('AYT', 'AYT')])
    branch = models.CharField(max_length=20, choices=[('SAY', 'Sayısal'), ('EA', 'Eşit Ağırlık'), ('SOZ', 'Sözel')])

    # Genel istatistikler
    total_tests = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    total_correct = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    best_score = models.FloatField(default=0.0)

    # Streak bilgileri
    current_streak = models.IntegerField(default=0)
    best_streak = models.IntegerField(default=0)
    last_test_date = models.DateTimeField(null=True, blank=True)

    # Detaylı istatistikler
    subject_mastery = models.JSONField(default=dict)  # {"MAT": {"correct": 45, "total": 50, "mastery": 0.9}}
    improvement_trend = models.FloatField(default=0.0)  # İyileşme trendi (+/-)

    # Zaman bilgileri
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Anonymous Statistics'
        verbose_name_plural = 'Anonymous Statistics'
        unique_together = [('anonymous_user', 'exam_type', 'branch')]
        indexes = [
            models.Index(fields=['anonymous_user', 'exam_type', 'branch']),
            models.Index(fields=['last_test_date']),
        ]

    def __str__(self):
        return f"{self.anonymous_user.browser_id[:8]} - {self.exam_type}/{self.branch}"

    def update_stats(self, test_result):
        """Test sonucuna göre istatistikleri güncelle"""
        self.total_tests += 1
        self.total_questions += test_result.total_questions
        self.total_correct += test_result.correct_count

        # Ortalama skor güncelle
        self.average_score = (self.total_correct / self.total_questions) * 100

        # En iyi skor güncelle
        if test_result.percentage > self.best_score:
            self.best_score = test_result.percentage

        # Streak güncelle
        self.last_test_date = timezone.now()

        # Subject mastery güncelle
        for subject, data in test_result.subject_breakdown.items():
            if subject not in self.subject_mastery:
                self.subject_mastery[subject] = {"correct": 0, "total": 0, "mastery": 0.0}

            self.subject_mastery[subject]["correct"] += data.get("correct", 0)
            self.subject_mastery[subject]["total"] += data.get("total", 0)

            if self.subject_mastery[subject]["total"] > 0:
                self.subject_mastery[subject]["mastery"] = (
                    self.subject_mastery[subject]["correct"] / self.subject_mastery[subject]["total"]
                )

        self.save()

    def get_improvement_suggestion(self):
        """İyileşme önerisi döndür"""
        if self.total_tests < 3:
            return "Keep practicing! More data needed for accurate suggestions."

        # En zayıf konuyu bul
        weakest_subject = min(
            self.subject_mastery.items(),
            key=lambda x: x[1]["mastery"] if x[1]["total"] > 0 else 0
        )

        if weakest_subject[1]["mastery"] < 0.7:
            return f"Focus on {weakest_subject[0]} (mastery: {weakest_subject[1]['mastery']:.1%})"

        return f"Great job! Your average score is {self.average_score:.1f}%"