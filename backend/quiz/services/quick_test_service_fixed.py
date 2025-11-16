def generate_quick_test_questions(session):
    """
    Generate questions for a quick test session
    """
    from quiz.models import Question, Subject

    created_questions = []
    current_order = 1

    try:
        # Get test configuration from session
        test_config = session.test_config
        subjects_config = test_config.get('subjects', {})

        # Calculate total questions needed
        total_questions = sum(subjects_config.values())

        # If no subject configuration, use default
        if not subjects_config:
            subjects_config = {
                'TURKCE': 3,
                'MATEMATIK': 3,
                'FEN': 2,
                'SOSYAL': 2
            }

        # Generate questions for each subject
        for subject_code, questions_count in subjects_config.items():
            try:
                subject = Subject.objects.get(code=subject_code)
                questions = Question.objects.filter(subject=subject).order_by('?')[:questions_count]

                for question in questions:
                    # Convert choices to JSON format
                    choices = {}
                    for choice in question.choices.all():
                        choices[choice.label] = choice.text

                    # Create temporary exam question
                    temp_question = TempExamQuestion.objects.create(
                        session=session,
                        question_text=question.question_text,
                        options=choices,
                        correct_option=question.correct_answer,
                        subject=subject.name,
                        topic=question.topic.name if question.topic else None,
                        difficulty=str(question.difficulty),
                        order=current_order
                    )
                    created_questions.append(temp_question)
                    current_order += 1

            except Subject.DoesNotExist:
                continue
            except Exception as e:
                continue

    except Exception as e:
        pass

    return created_questions