#!/usr/bin/env python
import os
import sys
import django
import uuid
import random
from typing import Dict, List, Any
from pathlib import Path

# Django'ı ayarla
sys.path.append('/mnt/c/Users/kur06/Downloads/osym_ai/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osym_ai.settings')
django.setup()

from quiz.models import Question, Subject, Topic, Choice, PDFDocument
from langchain_community.document_loaders import PyPDFLoader


class SoruUretimServisi:
    """
    PDF'lerdeki soruları şablon olarak kullanarak
    ÖSYM tarzı yeni sorular üreten servis
    """

    def __init__(self):
        self.sablon_sorular = []
        self.soru_sablonlari = {}

    def pdflerden_sablonlari_ayikla(self):
        """
        PDF'lerden soru yapılarını ayıklayıp şablon olarak kaydeder
        """
        try:
            pdf_documents = PDFDocument.objects.filter(document_type='PAST_EXAM')
            print(f"{pdf_documents.count()} PDF işleniyor...")

            for pdf in pdf_documents:
                print(f"İşleniyor: {pdf.title}")
                sorular = self._pdf_sorularini_ayikla(pdf)
                self.sablon_sorular.extend(sorular)

            print(f"Toplam {len(self.sablon_sorular)} şablon soru ayıklandı")

            # Şablonları konulara göre grupla
            self._sablonlari_grupla()

            return True

        except Exception as e:
            print(f"PDF şablon ayıklama hatası: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _pdf_sorularini_ayikla(self, pdf_document):
        """
        Bir PDF dosyasından soru yapılarını ayıklar
        """
        sorular = []

        try:
            # PDF dosyasının yolunu al
            pdf_path = pdf_document.file.path
            if not os.path.exists(pdf_path):
                print(f"PDF dosyası bulunamadı: {pdf_path}")
                return sorular

            # PDF'i yükle
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()

            # Sayfaları birleştirerek tam metin oluştur
            full_text = "\n".join([page.page_content for page in pages])

            # Soru kalıplarını bul
            soru_bloklari = self._metinden_soru_bloklari_ayikla(full_text)

            for blok in soru_bloklari:
                soru = self._soruyu_parcala(blok, pdf_document.title)
                if soru:
                    sorular.append(soru)

        except Exception as e:
            print(f"PDF okuma hatası ({pdf_document.title}): {e}")

        return sorular

    def _metinden_soru_bloklari_ayikla(self, text):
        """
        Metinden soru bloklarını ayıklar
        """
        soru_bloklari = []

        # Soru başlangıç kalıpları
        soru_baslangiclari = [
            r'\d+\.\s*Aşagıdaki\s+parçaya\s+göre',
            r'\d+\.\s*Aşağıdaki\s+parçaya\s+göre',
            r'\d+\.\s*Aşağıdaki\s+verilere\s+göre',
            r'\d+\.\s*Birlikte\s+yapılan',
            r'\d+\.\s*Verilen',
            r'\d+\.\s*Aşağıdakilerden',
        ]

        # Soru bitiş kalıpları (şıklar başlangıcı)
        secenek_baslangiclari = [
            r'A\)',
            r'B\)',
            r'C\)',
            r'D\)',
            r'E\)',
            r'A\.',
            r'B\.',
            r'C\.',
            r'D\.',
            r'E\.',
        ]

        import re

        # Metni temizle
        text = text.replace('\n', ' ').replace('\r', ' ')

        # Soru bloklarını bul
        for pattern in soru_baslangiclari:
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                start_pos = match.start()

                # Şıkların başlangıcını bul
                secenek_baslangici = -1
                for sec_pattern in secenek_baslangiclari:
                    sec_match = re.search(sec_pattern, text[start_pos:start_pos+500])
                    if sec_match:
                        secenek_baslangici = start_pos + sec_match.start()
                        break

                if secenek_baslangici > start_pos:
                    # Soru bloğunu al
                    soru_metni = text[start_pos:secenek_baslangici].strip()

                    # Şıkları ve cevabı bul
                    secenekler_bitis = text.find('Cevap:', secenek_baslangici)
                    if secenekler_bitis == -1:
                        secenekler_bitis = text.find('Doğru Cevap:', secenek_baslangici)
                    if secenekler_bitis == -1:
                        secenekler_bitis = min(secenek_baslangici + 300, len(text))

                    secenekler_metni = text[secenek_baslangici:secenekler_bitis].strip()

                    # Cevabı bul
                    cevap_basi = text.find('Cevap:', secenekler_bitis)
                    if cevap_basi == -1:
                        cevap_basi = text.find('Doğru Cevap:', secenekler_bitis)

                    if cevap_basi != -1:
                        cevap_son = cevap_basi + 50
                        cevap_metni = text[cevap_basi:cevap_son]

                        # Doğru şıkkı bul
                        dogru_sik = 'A'  # varsayılan
                        for sik in ['A', 'B', 'C', 'D', 'E']:
                            if f'{sik})' in cevap_metni or f'{sik}.' in cevap_metni:
                                dogru_sik = sik
                                break
                    else:
                        dogru_sik = 'C'  # varsayılan

                    tam_blok = soru_metni + "\n" + secenekler_metni + f"\nCevap: {dogru_sik}"
                    soru_bloklari.append(tam_blok)

        return soru_bloklari

    def _soruyu_parcala(self, soru_metni, pdf_basligi):
        """
        Soru metnini parçalara ayırır: soru kökü, şıklar, doğru cevap
        """
        try:
            import re

            # Doğru cevabı bul
            dogru_cevap = 'C'  # varsayılan
            cevap_esles = re.search(r'Cevap:\s*([A-E])', soru_metni, re.IGNORECASE)
            if cevap_esles:
                dogru_cevap = cevap_esles.group(1).upper()

            # Şıkları ayır
            secenekler = {}
            soru_koku = ""

            # Şık kalıpları
            secenek_pattern = r'([A-E])[\)\.]\s*([^A-E]*?)(?=[A-E][\)\.]|$)'
            secenek_esles = re.findall(secenek_pattern, soru_metni, re.IGNORECASE)

            if len(secenek_esles) >= 4:  # En az 4 şık varsa
                for sik, metin in secenek_esles:
                    # Şık metnini temizle
                    metin = re.sub(r'Cevap:\s*[A-E].*', '', metin, flags=re.IGNORECASE).strip()
                    if metin:
                        secenekler[sik.upper()] = metin[:200]  # Maksimum 200 karakter

                # Soru kökünü çıkar (şıklardan önceki kısım)
                ilk_secenek_esles = re.search(r'[A-E][\)\.]', soru_metni)
                if ilk_secenek_esles:
                    soru_koku = soru_metni[:ilk_secenek_esles.start()].strip()
                    soru_koku = re.sub(r'^\d+[\.\)]\s*', '', soru_koku)  # Numarayı kaldır
            else:
                # Basit ayırma
                parcalar = soru_metni.split('\n')
                if len(parcalar) >= 3:
                    soru_koku = parcalar[0]
                    secenekler = {'A': parcalar[1], 'B': parcalar[2], 'C': parcalar[3] if len(parcalar) > 3 else '', 'D': parcalar[4] if len(parcalar) > 4 else ''}

            # Konuyu belirle
            konu = self._konu_tespit_et(pdf_basligi, soru_koku)

            # Zorluk belirle
            zorluk = self._zorluk_tespit_et(soru_koku)

            return {
                'soru_koku': soru_koku,
                'secenekler': secenekler,
                'dogru_cevap': dogru_cevap,
                'konu': konu,
                'zorluk': zorluk,
                'kaynak': pdf_basligi
            }

        except Exception as e:
            print(f"Soru parçalama hatası: {e}")
            return None

    def _konu_tespit_et(self, pdf_basligi, soru_metni):
        """
        Soru metninden konu tespiti yapar
        """
        pdf_basligi_lower = pdf_basligi.lower()
        soru_metni_lower = soru_metni.lower()

        # Türkçe konuları
        if 'türkçe' in pdf_basligi_lower or any(x in soru_metni_lower for x in ['paragraf', 'anlam', 'sözcük', 'cümle']):
            if 'paragraf' in soru_metni_lower:
                return 'Paragraf Soruları'
            elif 'anlam' in soru_metni_lower:
                return 'Anlam Bilgisi'
            else:
                return 'Yazım Kuralları'

        # Matematik konuları
        elif 'matematik' in pdf_basligi_lower or any(x in soru_metni_lower for x in ['denklem', 'fonksiyon', 'sayı', 'problem']):
            if 'denklem' in soru_metni_lower or 'fonksiyon' in soru_metni_lower:
                return 'Fonksiyonlar ve Denklemler'
            elif 'problem' in soru_metni_lower:
                return 'Problemler'
            else:
                return 'Temel Kavramlar'

        # Fizik konuları
        elif 'fizik' in pdf_basligi_lower:
            if 'elektrik' in soru_metni_lower:
                return 'Elektrik'
            elif 'mekanik' in soru_metni_lower:
                return 'Mekanik'
            else:
                return 'Genel Fizik'

        # Kimya konuları
        elif 'kimya' in pdf_basligi_lower:
            if 'maddenin halleri' in soru_metni_lower:
                return 'Maddenin Halleri'
            elif 'element' in soru_metni_lower:
                return 'Periyodik Sistem'
            else:
                return 'Genel Kimya'

        # Biyoloji konuları
        elif 'biyoloji' in pdf_basligi_lower:
            if 'hücre' in soru_metni_lower:
                return 'Hücre'
            elif 'dna' in soru_metni_lower:
                return 'Genetik'
            else:
                return 'Canlılar Dünyası'

        # Tarih konuları
        elif 'tarih' in pdf_basligi_lower:
            if 'ataturk' in soru_metni_lower or 'inkılap' in soru_metni_lower:
                return 'Atatürk İnkılapları'
            elif 'osmanlı' in soru_metni_lower:
                return 'Osmanlı Tarihi'
            else:
                return 'Genel Tarih'

        return 'Genel Konu'

    def _zorluk_tespit_et(self, soru_metni):
        """
        Soru metninden zorluk seviyesi tespiti yapar
        """
        metin_lower = soru_metni.lower()

        # Kolay soru belirtileri
        kolay_ifadeler = ['hangisidir', 'nedir', 'kaç tane', 'hangi']
        orta_ifadeler = ['aşağıdakilerden', 'göre', 'verilere göre']
        zor_ifadeler = ['bileşke', 'entegrasyon', 'türev', 'logaritma', 'trigonometrik']

        kolay_skor = sum(1 for ifade in kolay_ifadeler if ifade in metin_lower)
        orta_skor = sum(1 for ifade in orta_ifadeler if ifade in metin_lower)
        zor_skor = sum(1 for ifade in zor_ifadeler if ifade in metin_lower)

        if zor_skor > 0:
            return 5  # Zor
        elif orta_skor > kolay_skor:
            return 3  # Orta
        else:
            return 1  # Kolay

    def _sablonlari_grupla(self):
        """
        Şablonları konulara göre gruplar
        """
        for sablon in self.sablon_sorular:
            konu = sablon['konu']
            if konu not in self.soru_sablonlari:
                self.soru_sablonlari[konu] = []
            self.soru_sablonlari[konu].append(sablon)

        print(f"Şablonlar {len(self.soru_sablonlari)} konuya gruplandı:")
        for konu, sablonlar in self.soru_sablonlari.items():
            print(f"  {konu}: {len(sablonlar)} şablon")

    def yeni_sorular_uret(self, konu, adet, zorluk=None):
        """
        Belirtilen konu ve adette yeni sorular üretir
        """
        if konu not in self.soru_sablonlari:
            print(f"Bu konu için şablon bulunamadı: {konu}")
            return []

        sablonlar = self.soru_sablonlari[konu]
        uretilen_sorular = []

        for i in range(adet):
            # Rastgele şablon seç
            sablon = random.choice(sablonlar)

            # Yeni soru üret
            yeni_soru = self._sablon_kullanarak_soru_uret(sablon, zorluk)
            if yeni_soru:
                uretilen_sorular.append(yeni_soru)

        return uretilen_sorular

    def _sablon_kullanarak_soru_uret(self, sablon, istenen_zorluk=None):
        """
        Şablon kullanarak yeni bir soru üretir
        """
        try:
            # Orijinal soruyu al
            soru_koku = sablon['soru_koku']
            secenekler = sablon['secenekler']
            dogru_cevap = sablon['dogru_cevap']
            konu = sablon['konu']

            # Zorluk ayarla
            zorluk = istenen_zorluk or sablon['zorluk']

            # Soru varyasyonu oluştur
            yeni_soru_koku = self._soru_varyasyonu_olustur(soru_koku, zorluk)
            yeni_secenekler = self._secenek_varyasyonu_olustur(secenekler, zorluk)

            # Doğru cevabı rastgele değiştir (ama şıklar arasında olmalı)
            secenek_listesi = list(yeni_secenekler.keys())
            if dogru_cevap in yeni_secenekler:
                yeni_dogru_cevap = dogru_cevap
            else:
                yeni_dogru_cevap = random.choice(secenek_listesi)

            # Subject ve Topic belirle
            subject = self._konudan_subject_bul(konu)
            topic = self._konudan_topic_bul(subject, konu)

            if not subject or not topic:
                print(f"Konu için subject/topic bulunamadı: {konu}")
                return None

            # Veritabanına kaydet
            soru_id = self._soru_id_olustur(subject.code, konu)

            question = Question.objects.create(
                id=soru_id,
                subject=subject,
                topic=topic,
                question_text=yeni_soru_koku,
                difficulty=zorluk,
                cognitive='Kavrama',
                correct_answer=yeni_dogru_cevap
            )

            # Şıkları oluştur
            for label, text in yeni_secenekler.items():
                Choice.objects.create(
                    question=question,
                    label=label,
                    text=text,
                    is_correct=(label == yeni_dogru_cevap)
                )

            print(f"Yeni soru üretildi: {soru_id}")
            return question

        except Exception as e:
            print(f"Soru üretim hatası: {e}")
            return None

    def _soru_varyasyonu_olustur(self, orijinal_metin, zorluk):
        """
        Soru metni için varyasyon oluşturur
        """
        varyasyonlar = [
            orijinal_metin,
            orijinal_metin.replace("aşağıdaki", "verilen"),
            orijinal_metin.replace("parçaya göre", "metne göre"),
            orijinal_metin.replace("hangisidir", "doğru olanı aşağıdakilerden hangisidir"),
        ]

        # Basit varyasyonlar
        yeni_metin = random.choice(varyasyonlar)

        # Zorluk seviyesine göre eklemeler
        if zorluk >= 4:  # Zor sorular
            ekler = [
                " Aşağıdaki çoktan seçmeli soruyu dikkatlice okuyunuz.",
                " Bu soruda dikkatli analiz yapmanız gerekmektedir.",
            ]
            yeni_metin += random.choice(ekler)

        return yeni_metin

    def _secenek_varyasyonu_olustur(self, orijinal_secenekler, zorluk):
        """
        Şıklar için varyasyon oluşturur
        """
        yeni_secenekler = {}

        for sik, metin in orijinal_secenekler.items():
            # Şık metnini biraz değiştir
            varyasyonlu_metin = metin

            # Basit varyasyonlar
            varyasyonlar = [
                metin,
                metin + " olabilir.",
                metin + " olarak kabul edilebilir.",
                "Verilen metne göre " + metin.lower(),
            ]

            varyasyonlu_metin = random.choice(varyasyonlar)
            yeni_secenekler[sik] = varyasyonlu_metin

        return yeni_secenekler

    def _konudan_subject_bul(self, konu):
        """
        Konu adına göre Subject nesnesi bulur
        """
        from quiz.models import Subject

        konu_lower = konu.lower()

        if 'türkçe' in konu_lower or 'paragraf' in konu_lower or 'anlam' in konu_lower:
            return Subject.objects.get(code='TR')
        elif 'matematik' in konu_lower or 'fonksiyon' in konu_lower or 'denklem' in konu_lower:
            return Subject.objects.get(code='MAT')
        elif 'fizik' in konu_lower:
            return Subject.objects.get(code='FIZ')
        elif 'kimya' in konu_lower:
            return Subject.objects.get(code='KIM')
        elif 'biyoloji' in konu_lower or 'hücre' in konu_lower:
            return Subject.objects.get(code='BIO')
        elif 'tarih' in konu_lower:
            return Subject.objects.get(code='TAR')
        elif 'coğrafya' in konu_lower:
            return Subject.objects.get(code='COG')

        return None

    def _konudan_topic_bul(self, subject, konu):
        """
        Subject ve konu adına göre Topic nesnesi bulur
        """
        from quiz.models import Topic

        # İlk olarak tam eşleşme ara
        try:
            return Topic.objects.get(subject=subject, name=konu)
        except Topic.DoesNotExist:
            pass

        # Konu adına göre en yakın topic'i bul
        konu_lower = konu.lower()

        if subject.code == 'TR':
            if 'paragraf' in konu_lower:
                return Topic.objects.get(subject=subject, name='Paragraf Soruları')
            elif 'anlam' in konu_lower:
                return Topic.objects.get(subject=subject, name='Anlam Bilgisi')
        elif subject.code == 'MAT':
            if 'fonksiyon' in konu_lower or 'denklem' in konu_lower:
                return Topic.objects.get(subject=subject, name='Fonksiyonlar')
            elif 'problem' in konu_lower:
                return Topic.objects.get(subject=subject, name='Problemler')
            else:
                return Topic.objects.get(subject=subject, name='Temel Kavramlar')
        elif subject.code == 'FIZ':
            if 'elektrik' in konu_lower:
                return Topic.objects.get(subject=subject, name='Elektrik')
            else:
                return Topic.objects.get(subject=subject, name='Mekanik')
        elif subject.code == 'KIM':
            if 'maddenin' in konu_lower:
                return Topic.objects.get(subject=subject, name='Maddenin Halleri')
            else:
                return Topic.objects.get(subject=subject, name='Kimyasal Hesaplamalar')
        elif subject.code == 'BIO':
            if 'hücre' in konu_lower:
                return Topic.objects.get(subject=subject, name='Hücre')
            else:
                return Topic.objects.get(subject=subject, name='Canlılar Dünyası')
        elif subject.code == 'TAR':
            if 'ataturk' in konu_lower or 'inkılap' in konu_lower:
                return Topic.objects.get(subject=subject, name='Atatürk İnkılapları')
            else:
                return Topic.objects.get(subject=subject, name='Osmanlı Tarihi')

        # Hiçbiri bulunamazsa ilk topic'i dön
        return Topic.objects.filter(subject=subject).first()

    def _soru_id_olustur(self, subject_code, konu_adi):
        """
        Benzersiz soru ID'si oluşturur
        """
        konu_kisaltma = konu_adi.replace(' ', '')[:15]
        random_num = random.randint(10000, 99999)
        return f"{subject_code}-{konu_kisaltma}-{random_num}"

    def konu_bazinda_soru_uret(self, min_soru_sayisi=20):
        """
        Her konu için minimum belirtilen sayıda soru üretir
        """
        print("Konu bazında soru üretimi başlatılıyor...")

        uretilen_toplam = 0

        for konu, sablonlar in self.soru_sablonlari.items():
            if len(sablonlar) == 0:
                continue

            # Her konu için 20-30 soru üret
            adet = max(min_soru_sayisi, len(sablonlar) * 3)

            print(f"\n{konu} için {adet} soru üretiliyor...")
            yeni_sorular = self.yeni_sorular_uret(konu, adet)
            uretilen_toplam += len(yeni_sorular)

        print(f"\nToplam {uretilen_toplam} yeni soru üretildi!")
        return uretilen_toplam


def main():
    """
    Ana fonksiyon - soru üretim sürecini başlatır
    """
    print("ÖYSM Tarzı Soru Üretim Sistemi")
    print("=" * 40)

    servisi = SoruUretimServisi()

    # 1. PDF'lerden şablonları ayıkla
    if servisi.pdflerden_sablonlari_ayikla():
        print("✓ Şablon ayıklama başarılı")
    else:
        print("✗ Şablon ayıklama başarısız")
        return

    # 2. Konu bazında sorular üret
    uretilen_adet = servisi.konu_bazinda_soru_uret(min_soru_sayisi=15)

    # 3. Veritabanındaki toplam soru sayısını kontrol et
    from quiz.models import Question
    toplam_soru = Question.objects.count()
    print(f"\nVeritabanındaki toplam soru sayısı: {toplam_soru}")

    # Konu dağılımını göster
    from quiz.models import Subject
    print("\nSoru dağılımı:")
    print("-" * 30)
    for subject in Subject.objects.all():
        sayi = Question.objects.filter(subject=subject).count()
        if sayi > 0:
            print(f"{subject.name}: {sayi} soru")


if __name__ == "__main__":
    main()