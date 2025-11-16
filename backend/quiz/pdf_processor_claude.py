def analyze_curriculum_content(pdf_document, chunks):
    """
    Claude ile müfredat içeriğini analiz eder (OpenAI olmadan)
    """
    try:
        print(f"Analyzing curriculum content for {pdf_document.title}")
        
        # Basit metin analizi
        full_text = " ".join([chunk.page_content for chunk in chunks])
        
        # Anahtar kelimeleri çıkar
        keywords = extract_keywords_from_text(full_text)
        
        # İçerik özeti oluştur
        summary = generate_content_summary(full_text)
        
        print(f"Successfully analyzed curriculum: {len(chunks)} chunks, {len(keywords)} keywords")
        
    except Exception as e:
        print(f"Error analyzing curriculum content: {e}")


def extract_keywords_from_text(text):
    """Metinden anahtar kelimeleri çıkarır"""
    yks_terms = [
        "fonksiyon", "türev", "integral", "limit", "logaritma",
        "paragraf", "anlam bilgis", "cumle analizi",
        "elektrik", "manyetizma", "mekanik",
        "osmanli", "cumhuriyet", "inkilap",
        "cografya", "turkiye", "kimya", "biyoloji"
    ]
    
    text_lower = text.lower()
    keywords = [term for term in yks_terms if term in text_lower]
    return keywords[:20]


def generate_content_summary(text):
    """Metin için içerik özeti oluşturur"""
    if len(text) > 500:
        return text[:500] + "..."
    return text.strip()
