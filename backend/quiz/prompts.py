SYSTEM_PROMPT = (
"Sen Türkiye YKS (TYT-AYT) için soru üretim ve çözüm asistanısın. "
"Her soruda 1 doğru + 4 çeldirici olacak. Çözüm rubriği adım adım ve hatasız olsun."
)


USER_TEMPLATE = (
"Ders: {subject}\nKonu: {topic}\nZorluk: {difficulty}\n"
"Tür: Çoktan seçmeli. Biçim: JSON. Alanlar: stem, choices[5], answer, rubric. "
"Seçenekleri 'A) ...' formatında ver."
)