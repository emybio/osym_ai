from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from .models import PastQuestion


def build_past_question_embeddings(persist_directory="chroma_past"):
    """
    Tüm PastQuestion kayıtlarını alır, embedding oluşturur ve Chroma veritabanına kaydeder.
    """
    questions = PastQuestion.objects.all()
    if not questions.exists():
        print("Geçmiş soru bulunamadı, embedding oluşturulmadı.")
        return

    texts = [
        f"{q.subject.name} {q.topic.name}: {q.question_text}"
        for q in questions
    ]
    metadatas = [
        {
            "subject": q.subject.code,
            "topic": q.topic.name,
            "year": q.year,
            "exam": q.exam,
        }
        for q in questions
    ]

    embeddings = OpenAIEmbeddings()
    db = Chroma.from_texts(texts, embeddings, metadatas=metadatas, persist_directory=persist_directory)
    db.persist()
    print(f"{len(texts)} geçmiş soru için embedding oluşturuldu.")