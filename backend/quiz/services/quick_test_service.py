import random
from quiz.models import TempExamResult, ExamResult, TempExamSession, AnonymousUser
from .anonymous_user_service import AnonymousUserService


def merge_temp_results(temp_result_uuid, user):
    """
    Geçici test sonucunu kalıcı kullanıcıya merge eder.

    Args:
        temp_result_uuid (UUID): TempExamResult uuid'si
        user (User): Django User modeli

    Returns:
        tuple: (success: bool, message: str, exam_result: ExamResult/None)
    """
    try:
        # Geçici sonucu al
        temp_result = TempExamResult.objects.get(
            uuid=temp_result_uuid,
            merged=False
        )
        session = temp_result.session

        # Kalıcı sonucu oluştur
        exam_result = ExamResult.objects.create(
            user=user,
            source_uuid=temp_result_uuid,
            exam_type=session.exam_type,
            branch=session.branch,
            total_questions=temp_result.total_questions,
            correct_count=temp_result.correct_count,
            wrong_count=temp_result.wrong_count,
            percentage=temp_result.percentage,
            subject_breakdown=temp_result.subject_breakdown,
            is_quick_test=True
        )

        # Geçici sonucu ve oturumu güncelle
        temp_result.merged = True
        temp_result.save()

        session.status = "merged"
        session.save()

        return True, "Test sonucu başarıyla hesabınıza eklendi.", exam_result

    except TempExamResult.DoesNotExist:
        return False, "Geçersiz veya daha önce birleştirilmiş test sonucu.", None
    except Exception as e:
        return False, f"Birleştirme işlemi sırasında hata: {str(e)}", None


def generate_quick_test_questions(session, user_identifier=None):
    """
    Hızlı test için sorular oluşturur.
    Akıllı soru seçim algoritması kullanarak kullanıcıya önce görmediği soruları sunar.

    Args:
        session (TempExamSession): Test oturumu
        user_identifier (str): Kullanıcıyı tanımlayan unique ID (IP, session key, etc.)

    Returns:
        list: Oluşturulan TempExamQuestion nesneleri
    """
    from quiz.models import Question, TempExamQuestion, Subject
    from .smart_question_selection import smart_selector

    try:
        # Akıllı soru seçiciyi kullanarak soruları getir
        selected_questions = smart_selector.get_questions_for_user(
            session=session,
            user_identifier=user_identifier
        )

        created_questions = []
        current_order = 1

        # Seçilen soruları TempExamQuestion'a dönüştür
        for question in selected_questions:
            # Seçenekleri JSON formatına çevir
            choices = {}
            for choice in question.choices.all():
                choices[choice.label] = choice.text

            temp_question = TempExamQuestion.objects.create(
                session=session,
                question_text=question.question_text,
                options=choices,
                correct_option=question.correct_answer,
                subject=question.subject.name,
                topic=question.topic.name if question.topic else None,
                difficulty=str(question.difficulty),
                order=current_order
            )
            created_questions.append(temp_question)
            current_order += 1

        return created_questions

    except Exception as e:
        print(f"Error in smart question selection, falling back to random: {e}")
        # Hata durumunda eski random metoda geri dönüş
        return _fallback_random_selection(session)


def _fallback_random_selection(session):
    """
    Akıllı seçim hata verdiğinde kullanılacak rastgele soru seçimi
    """
    from quiz.models import Question, TempExamQuestion, Subject

    # Basit rastgele seçim - ilk 42 sorudan rastgele seç
    all_questions = Question.objects.all()
    if all_questions.count() < session.question_count:
        selected_questions = list(all_questions)
    else:
        selected_questions = random.sample(list(all_questions), session.question_count)

    created_questions = []
    current_order = 1

    for question in selected_questions:
        choices = {}
        for choice in question.choices.all():
            choices[choice.label] = choice.text

        temp_question = TempExamQuestion.objects.create(
            session=session,
            question_text=question.question_text,
            options=choices,
            correct_option=question.correct_answer,
            subject=question.subject.name,
            topic=question.topic.name if question.topic else None,
            difficulty=str(question.difficulty),
            order=current_order
        )
        created_questions.append(temp_question)
        current_order += 1

    return created_questions


def calculate_temp_exam_result(session, answers):
    """
    Hızlı test sonuçlarını hesaplar.

    Args:
        session (TempExamSession): Test oturumu
        answers (dict): {question_id: "A", ...}

    Returns:
        TempExamResult: Oluşturulan sonuç nesnesi
    """
    questions = session.questions.all()
    correct_count = 0
    subject_breakdown = {}

    for question in questions:
        # Cevabı kontrol et
        selected_answer = answers.get(str(question.id), "")
        is_correct = selected_answer == question.correct_option

        if is_correct:
            correct_count += 1

        # Konu bazında hesapla
        subject = question.subject
        if subject not in subject_breakdown:
            subject_breakdown[subject] = {"correct": 0, "total": 0}

        subject_breakdown[subject]["total"] += 1
        if is_correct:
            subject_breakdown[subject]["correct"] += 1

    total_questions = len(questions)
    wrong_count = total_questions - correct_count
    percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0

    # Sonuç nesnesini oluştur
    result = TempExamResult.objects.create(
        session=session,
        total_questions=total_questions,
        correct_count=correct_count,
        wrong_count=wrong_count,
        percentage=round(percentage, 2),
        subject_breakdown=subject_breakdown
    )

    # Oturum durumunu güncelle
    session.status = "completed"
    session.save()

    return result


def create_temp_exam_with_anonymous_user(session_data, request, anonymous_user):
    """
    Anonim kullanıcı ile geçici sınav oturumu ve sonuçları oluştur
    """
    from django.http import HttpResponse

    # Anonim kullanıcıyı session'a bağla
    session_data.anonymous_user = anonymous_user
    session_data.save()

    # Soruları oluştur
    questions = generate_quick_test_questions(session_data)

    return questions


def save_temp_result_with_anonymous_user(session, answers, request, anonymous_user):
    """
    Anonim kullanıcı ile test sonucunu kaydet ve istatistikleri güncelle
    """
    from django.utils import timezone
    from quiz.models import AnonymousStats

    # Cevapları kontrol et
    correct_count = 0
    wrong_count = 0
    subject_breakdown = {}

    for question in session.questions.all():
        user_answer = answers.get(str(question.order))
        is_correct = user_answer == question.correct_option

        if is_correct:
            correct_count += 1
        else:
            wrong_count += 1

        # Subject breakdown güncelle
        subject = question.subject
        if subject not in subject_breakdown:
            subject_breakdown[subject] = {"correct": 0, "total": 0}

        subject_breakdown[subject]["total"] += 1
        if is_correct:
            subject_breakdown[subject]["correct"] += 1

    percentage = (correct_count / session.question_count) * 100 if session.question_count > 0 else 0

    # Sonuç oluştur
    result = TempExamResult.objects.create(
        session=session,
        # TODO: Add anonymous_user field when properly implemented
        # anonymous_user=anonymous_user,
        total_questions=session.question_count,
        correct_count=correct_count,
        wrong_count=wrong_count,
        percentage=round(percentage, 2),
        subject_breakdown=subject_breakdown
    )

    # Oturumu tamamlandı olarak işaretle
    session.status = 'completed'
    session.save()

    # AnonymousUser test sayısını güncelle
    anonymous_user.update_test_count()

    # İstatistikleri güncelle
    stats, created = AnonymousStats.objects.get_or_create(
        anonymous_user=anonymous_user,
        exam_type=session.exam_type,
        branch=session.branch
    )
    stats.update_stats(result)

    # User integrity kontrolü (optional)
    if not AnonymousUserService.verify_user_integrity(request, anonymous_user):
        # Şüpheli aktivite, kullanıcıyı block'la
        AnonymousUserService.block_user(
            anonymous_user,
            hours=24,
            reason="Suspicious activity detected"
        )

    return result


def get_anonymous_user_dashboard_data(request):
    """
    Anonim kullanıcı dashboard verileri
    """
    anonymous_user = AnonymousUserService.get_anonymous_user(request)
    if not anonymous_user:
        return None

    return AnonymousUserService.get_user_dashboard_data(anonymous_user)


def cleanup_old_sessions(days=7):
    """
    Eski tamamlanmamış oturumları temizle
    """
    from django.utils import timezone

    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    deleted_count = TempExamSession.objects.filter(
        created_at__lt=cutoff_date,
        status='active'
    ).delete()

    return deleted_count


def get_anonymous_user_limits(request):
    """
    Anonim kullanıcının test limitlerini döndür
    """
    anonymous_user = AnonymousUserService.get_anonymous_user(request)
    if not anonymous_user:
        return {
            'can_take_test': True,
            'daily_limit': 5,
            'daily_used': 0,
            'weekly_limit': 20,
            'weekly_used': 0,
            'remaining_today': 5,
            'remaining_this_week': 20,
            'is_blocked': False,
            'block_reason': None
        }

    can_take, message = AnonymousUserService.can_take_test(anonymous_user)

    return {
        'can_take_test': can_take,
        'daily_limit': 5,
        'daily_used': anonymous_user.daily_test_count,
        'weekly_limit': 20,
        'weekly_used': anonymous_user.weekly_test_count,
        'remaining_today': max(0, 5 - anonymous_user.daily_test_count),
        'remaining_this_week': max(0, 20 - anonymous_user.weekly_test_count),
        'is_blocked': anonymous_user.is_blocked(),
        'block_reason': anonymous_user.block_reason if anonymous_user.is_blocked() else None,
        'blocked_until': anonymous_user.blocked_until,
        'message': message if not can_take else None
    }