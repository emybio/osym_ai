"""Mock service for development when API credits are exhausted"""

MOCK_QUESTIONS = [
    {
        "stem": "Bir sayının 2 katı 12 ise, bu sayı kaçtır?",
        "choices": ["A) 4", "B) 6", "C) 8", "D) 10", "E) 12"],
        "answer": "B",
        "rubric": "2x = 12 ise x = 12/2 = 6",
        "topic": "Temel Cebir",
        "difficulty": "Kolay"
    },
    {
        "stem": "Bir üçgenin iç açıları toplamı kaç derecedir?",
        "choices": ["A) 90°", "B) 120°", "C) 180°", "D) 270°", "E) 360°"],
        "answer": "C",
        "rubric": "Her üçgenin iç açıları toplamı 180°'dir.",
        "topic": "Geometri",
        "difficulty": "Kolay"
    },
    {
        "stem": "5 x 7 x 2 işleminin sonucu nedir?",
        "choices": ["A) 35", "B) 50", "C) 70", "D) 85", "E) 100"],
        "answer": "C",
        "rubric": "5 x 7 = 35, 35 x 2 = 70",
        "topic": "Çarpma",
        "difficulty": "Kolay"
    }
]

def get_mock_question():
    """Get a random mock question for development"""
    import random
    question = random.choice(MOCK_QUESTIONS)
    return {
        "stem": question["stem"],
        "choices": [choice[3:] for choice in question["choices"]],  # Remove "A) ", "B) " etc.
        "answer": question["answer"],
        "rubric": question["rubric"],
        "source": "mock"
    }

def get_mock_explanation(question_text, choices):
    """Get mock explanation for development"""
    return [
        f"1. Soruyu dikkatlice okuyalım: {question_text}",
        f"2. Şıkları değerlendirelim: {', '.join(choices)}",
        "3. Doğru adımla çözümü uygulayalım:",
        "4. Matematiksel işlemleri yapalım",
        "5. Doğru cevabı bulalım ve kontrol edelim"
    ]