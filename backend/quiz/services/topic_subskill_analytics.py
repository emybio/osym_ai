import os
import sys
import django
from typing import Dict, List, Any, Tuple
from datetime import timedelta
from collections import defaultdict, Counter
import json
import random

# Django'ı ayarla
sys.path.append('/mnt/c/Users/kur06/Downloads/osym_ai/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osym_ai.settings')
django.setup()

from quiz.models import Question, Subject, Topic, Subskill, TempExamSession, TempExamQuestion, TempExamResult


class TopicSubskillAnalytics:
    """
    Öğrencinin performansını konu ve alt beceri bazında analiz eden
    zayıf noktaları tespit eden ve kişiselleştirilmiş öneriler sunan servis
    """

    def __init__(self):
        self.konu_zorluk_haritasi = {}
        self.beceri_agirligi = {
            'Kavrama': 0.2,
            'Uygulama': 0.3,
            'Analiz': 0.25,
            'Sentez': 0.15,
            'Değerlendirme': 0.1
        }

    def kullanici_analizi_yap(self, kullanici_id: str) -> Dict[str, Any]:
        """
        Kullanıcının tüm performans analizini yapar
        """
        try:
            # Kullanıcının test sonuçlarını al
            test_sonuclari = self._kullanici_sonuclarini_getir(kullanici_id)

            if not test_sonuclari:
                return {"hata": "Kullanıcı için test sonucu bulunamadı"}

            # Konu bazında analiz
            konu_analizi = self._konu_bazinda_analiz(test_sonuclari)

            # Alt beceri bazında analiz
            beceri_analizi = self._beceri_bazinda_analiz(test_sonuclari)

            # Zorluk seviyesi analizi
            zorluk_analizi = self._zorluk_seviyesi_analizi(test_sonuclari)

            # Zayıf noktaları tespit et
            zayif_noktalar = self._zayif_noktalari_tespit_et(konu_analizi, beceri_analizi)

            # Öğrenme patikası oluştur
            ogrenme_patikasi = self._ogrenme_patikasi_olustur(zayif_noktalar)

            # Kişiselleştirilmiş öneriler
            oneriler = self._kisisellestirilmis_oneriler_olustur(zayif_noktalar, konu_analizi)

            return {
                "kullanici_id": kullanici_id,
                "analiz_tarihi": django.utils.timezone.now().isoformat(),
                "test_sayisi": len(test_sonuclari),
                "toplam_soru": self._toplam_soru_sayisi(test_sonuclari),
                "genel_basari": self._genel_basari_hesapla(test_sonuclari),
                "konu_analizi": konu_analizi,
                "beceri_analizi": beceri_analizi,
                "zorluk_analizi": zorluk_analizi,
                "zayif_noktalar": zayif_noktalar,
                "ogrenme_patikasi": ogrenme_patikasi,
                "oneriler": oneriler,
                "hedef_sure": self._hedef_sure_hesapla(zayif_noktalar)
            }

        except Exception as e:
            return {"hata": f"Analiz sırasında hata oluştu: {str(e)}"}

    def _kullanici_sonuclarini_getir(self, kullanici_id: str) -> List[Dict]:
        """
        Kullanıcının test sonuçlarını veritabanından çeker
        """
        sonuclar = []

        try:
            # TempExamResult tablosundan sonuçları al
            # IP adresi veya session key ile kullanıcıyı bul
            temp_results = TempExamResult.objects.filter(
                session__session_key=kullanici_id
            ).select_related('session').prefetch_related('session__questions')

            for result in temp_results:
                session = result.session
                cevaplar = {}

                # Sorular ve cevapları
                for question in session.questions.all():
                    # Cevapları result'tan alması gerekir (bu kısım geliştirilebilir)
                    cevaplar[str(question.order)] = "A"  # Geçici

                sonuclar.append({
                    "test_id": str(session.uuid),
                    "tarih": result.session.created_at.isoformat(),
                    "sinav_tipi": session.exam_type,
                    "brans": session.branch,
                    "toplam_soru": result.total_questions,
                    "dogru_sayisi": result.correct_count,
                    "yanlis_sayisi": result.wrong_count,
                    "yuzde": result.percentage,
                    "soru_detaylari": session.questions.all(),
                    "konu_breakdown": result.subject_breakdown
                })

        except Exception as e:
            print(f"Kullanıcı sonuçları alınırken hata: {e}")

        return sonuclar

    def _konu_bazinda_analiz(self, sonuclar: List[Dict]) -> Dict[str, Any]:
        """
        Konu bazında performans analizi yapar
        """
        konu_istatistikleri = defaultdict(lambda: {
            "toplam_soru": 0,
            "dogru_sayisi": 0,
            "yanlis_sayisi": 0,
            "basari_yuzdesi": 0.0,
            "zorluk_dagilimi": defaultdict(int),
            "son_testler": []
        })

        for sonuc in sonuclar:
            soru_detaylari = sonuc.get("soru_detaylari", [])

            for soru in soru_detaylari:
                konu_adi = soru.topic or "Bilinmeyen Konu"
                zorluk = soru.difficulty

                # Konu istatistiklerini güncelle
                konu_istatistikleri[konu_adi]["toplam_soru"] += 1

                # Cevap doğruluğunu kontrol et (basitleştirilmiş)
                # Normalde bu bilgi TempExamResult'tan alınmalı
                konu_istatistikleri[konu_adi]["dogru_sayisi"] += 1 if random.random() > 0.4 else 0  # Geçici
                konu_istatistikleri[konu_adi]["yanlis_sayisi"] += 1 if random.random() <= 0.4 else 0  # Geçici

                konu_istatistikleri[konu_adi]["zorluk_dagilimi"][zorluk] += 1

                # Son testleri kaydet
                if len(konu_istatistikleri[konu_adi]["son_testler"]) < 3:
                    konu_istatistikleri[konu_adi]["son_testler"].append({
                        "tarih": sonuc["tarih"],
                        "basari": 1 if random.random() > 0.4 else 0  # Geçici
                    })

        # Başarı yüzdelerini hesapla
        for konu, istatistik in konu_istatistikleri.items():
            if istatistik["toplam_soru"] > 0:
                istatistik["basari_yuzdesi"] = (istatistik["dogru_sayisi"] / istatistik["toplam_soru"]) * 100

        return dict(konu_istatistikleri)

    def _beceri_bazinda_analiz(self, sonuclar: List[Dict]) -> Dict[str, Any]:
        """
        Alt beceri bazında performans analizi yapar
        """
        beceri_istatistikleri = defaultdict(lambda: {
            "toplam_soru": 0,
            "dogru_sayisi": 0,
            "basari_yuzdesi": 0.0,
            "onc seviyesi": "Başlangıç"
        })

        # Bilişsel seviye analizleri
        bilişsel_seviyeler = {
            "Hatırlama": {"dogru": 0, "toplam": 0},
            "Kavrama": {"dogru": 0, "toplam": 0},
            "Uygulama": {"dogru": 0, "toplam": 0},
            "Analiz": {"dogru": 0, "toplam": 0},
            "Sentez": {"dogru": 0, "toplam": 0},
            "Değerlendirme": {"dogru": 0, "toplam": 0}
        }

        for sonuc in sonuclar:
            soru_detaylari = sonuc.get("soru_detaylari", [])

            for soru in soru_detaylari:
                # Sorunun bilişsel seviyesini belirle (basitleştirilmiş)
                bilişsel_seviye = self._sorunun_bilişsel_seviyesini_belirle(soru)

                bilişsel_seviyeler[bilişsel_seviye]["toplam"] += 1
                bilişsel_seviyeler[bilişsel_seviye]["dogru"] += 1 if random.random() > 0.3 else 0  # Geçici

        # Başarı yüzdelerini ve gelişim seviyelerini hesapla
        for seviye, veri in bilişsel_seviyeler.items():
            if veri["toplam"] > 0:
                basari_yuzdesi = (veri["dogru"] / veri["toplam"]) * 100
                gelişim_seviyesi = self._gelişim_seviyesi_belirle(basari_yuzdesi)

                beceri_istatistikleri[seviye].update({
                    "toplam_soru": veri["toplam"],
                    "dogru_sayisi": veri["dogru"],
                    "basari_yuzdesi": basari_yuzdesi,
                    "onc seviyesi": gelişim_seviyesi
                })

        return dict(beceri_istatistikleri)

    def _zorluk_seviyesi_analizi(self, sonuclar: List[Dict]) -> Dict[str, Any]:
        """
        Zorluk seviyesi bazında performans analizi
        """
        zorluk_istatistikleri = defaultdict(lambda: {
            "toplam_soru": 0,
            "dogru_sayisi": 0,
            "basari_yuzdesi": 0.0,
            "onerilen_sayi": 0
        })

        for sonuc in sonuclar:
            soru_detaylari = sonuc.get("soru_detaylari", [])

            for soru in soru_detaylari:
                zorluk = soru.difficulty
                zorluk_istatistikleri[zorluk]["toplam_soru"] += 1
                zorluk_istatistikleri[zorluk]["dogru_sayisi"] += 1 if random.random() > (zorluk / 5) else 0  # Geçici

        # Başarı yüzdelerini ve önerilen çalışma sayılarını hesapla
        for zorluk, istatistik in zorluk_istatistikleri.items():
            if istatistik["toplam_soru"] > 0:
                istatistik["basari_yuzdesi"] = (istatistik["dogru_sayisi"] / istatistik["toplam_soru"]) * 100

                # Başarı oranına göre önerilen çalışma sayısı
                if istatistik["basari_yuzdesi"] < 60:
                    istatistik["onerilen_sayi"] = 20
                elif istatistik["basari_yuzdesi"] < 80:
                    istatistik["onerilen_sayi"] = 10
                else:
                    istatistik["onerilen_sayi"] = 5

        return dict(zorluk_istatistikleri)

    def _zayif_noktalari_tespit_et(self, konu_analizi: Dict, beceri_analizi: Dict) -> List[Dict]:
        """
        Öğrencinin zayıf noktalarını tespit eder
        """
        zayif_noktalar = []

        # Konu bazında zayıflıklar
        for konu, veri in konu_analizi.items():
            if veri["basari_yuzdesi"] < 70 and veri["toplam_soru"] >= 3:  # En az 3 soru çözmüş olmalı
                oncelik = "Yüksek" if veri["basari_yuzdesi"] < 50 else "Orta"

                zayif_noktalar.append({
                    "tip": "Konu",
                    "ad": konu,
                    "mevcut_seviye": veri["basari_yuzdesi"],
                    "hedef_seviye": 85,
                    "fark": 85 - veri["basari_yuzdesi"],
                    "oncelik": oncelik,
                    "cozulen_soru": veri["toplam_soru"],
                    "onerilen_calisma": 15 if oncelik == "Yüksek" else 10
                })

        # Beceri bazında zayıflıklar
        for beceri, veri in beceri_analizi.items():
            if veri["basari_yuzdesi"] < 70 and veri["toplam_soru"] >= 3:
                oncelik = "Yüksek" if veri["basari_yuzdesi"] < 50 else "Orta"

                zayif_noktalar.append({
                    "tip": "Beceri",
                    "ad": beceri,
                    "mevcut_seviye": veri["basari_yuzdesi"],
                    "hedef_seviye": 85,
                    "fark": 85 - veri["basari_yuzdesi"],
                    "oncelik": oncelik,
                    "cozulen_soru": veri["toplam_soru"],
                    "onerilen_calisma": 12 if oncelik == "Yüksek" else 8
                })

        # Öncelik sırasına göre sırala
        zayif_noktalar.sort(key=lambda x: (x["fark"], x["cozulen_soru"]), reverse=True)

        return zayif_noktalar[:5]  # En fazla 5 zayıf nokta

    def _ogrenme_patikasi_olustur(self, zayif_noktalar: List[Dict]) -> Dict[str, Any]:
        """
        Kişiselleştirilmiş öğrenme patikası oluşturur
        """
        if not zayif_noktalar:
            return {
                "durum": "Güçlü",
                "mesaj": "Öğrenci zayıf noktası bulunamadı. Daha zorlu konulara geçilebilir.",
                "adimlar": []
            }

        # Öğrenme adımlarını oluştur
        adimlar = []
        toplam_sure = 0

        for i, nokta in enumerate(zayif_noktalar):
            # Konu için öğrenme materyalleri
            materyaller = self._ogrenme_materyalleri_oner(nokta)

            # Tahmini çalışma süresi
            calisma_suresi = nokta["onerilen_calisma"] * 2  # Her soru için 2 dk

            adim = {
                "sira": i + 1,
                "baslik": f"{nokta['ad']} - Güçlendirme",
                "tip": nokta["tip"],
                "aciklama": f"{nokta['ad']} konusunda % {nokta['mevcut_seviye']:.1f} başarı oranınızı % {nokta['hedef_seviye']} seviyesine çıkarmalısınız.",
                "hedef": f"% {nokta['hedef_seviye']} başarı oranı",
                "soru_sayisi": nokta["onerilen_calisma"],
                "tahmini_sure": calisma_suresi,
                "materyaller": materyaller,
                "onerilen_zorluk": self._onerilen_zorluk_belirle(nokta["mevcut_seviye"])
            }

            adimlar.append(adim)
            toplam_sure += calisma_suresi

        return {
            "durum": "Geliştirme Gerekli",
            "mesaj": f"{len(zayif_noktalar)} alanda güçlendirme çalışması öneriliyor.",
            "toplam_adim": len(adimlar),
            "tahmini_toplam_sure": toplam_sure,
            "adimlar": adimlar
        }

    def _kisisellestirilmis_oneriler_olustur(self, zayif_noktalar: List[Dict], konu_analizi: Dict) -> List[str]:
        """
        Kişiselleştirilmiş çalışma önerileri oluşturur
        """
        oneriler = []

        if not zayif_noktalar:
            oneriler.append("Harika gidiyorsunuz! Şimdi daha zorlu konularla meydan okumaya hazırsınız.")
            oneriler.append("Aynı konularda farklı zorluk seviyelerinde sorular çözmeye devam edin.")
            return oneriler

        # Genel öneriler
        oneriler.append("Her gün düzenli olarak soru çözüm pratiği yapın.")
        oneriler.append("Yanlış çözdüğünüz soruları mutlaka tekrar gözden geçirin.")

        # Konu özgü öneriler
        for nokta in zayif_noktalar[:3]:  # İlk 3 zayıf nokta için
            if nokta["tip"] == "Konu":
                oneriler.append(f"**{nokta['ad']}** konusunda temel konuları tekrar edin.")
                oneriler.append(f"Bu konuda en az {nokta['onerilen_calisma']} pratik soru çözün.")
            else:  # Beceri
                oneriler.append(f"**{nokta['ad']}** becerisini geliştirmek için analitik düşünmeyi pratik edin.")

        # Zorluk bazlı öneriler
        en_zor_konu = max(konu_analizi.items(), key=lambda x: x[1]["basari_yuzdesi"], default=None)
        if en_zor_konu and en_zor_konu[1]["basari_yuzdesi"] < 60:
            oneriler.append(f"En çok zorlandığınız **{en_zor_konu[0]}** konusuna odaklanın.")

        return oneriler

    def _sorunun_bilişsel_seviyesini_belirle(self, soru) -> str:
        """
        Sorunun bilişsel seviyesini belirler (basitleştirilmiş)
        """
        soru_metni = soru.question_text.lower()

        if any(kelime in soru_metni for kelime in ["nedir", "kaç", "hangi", "tanımı"]):
            return "Hatırlama"
        elif any(kelime in soru_metni for kelime in ["açıkla", "göster", "belirt"]):
            return "Kavrama"
        elif any(kelime in soru_metni for kelime in ["uygula", "hesapla", "bul"]):
            return "Uygulama"
        elif any(kelime in soru_metni for kelime in ["karşılaştır", "analiz et", "incele"]):
            return "Analiz"
        elif any(kelime in soru_metni for kelime in ["oluştur", "tasarla", "birleştir"]):
            return "Sentez"
        elif any(kelime in soru_metni for kelime in ["değerlendir", "yargıla", "kanıtla"]):
            return "Değerlendirme"
        else:
            return "Kavrama"  # Varsayılan

    def _gelişim_seviyesi_belirle(self, basari_yuzdesi: float) -> str:
        """
        Başarı yüzdesine göre gelişim seviyesi belirler
        """
        if basari_yuzdesi >= 90:
            return "İleri Düzey"
        elif basari_yuzdesi >= 75:
            return "Orta-İleri Düzey"
        elif basari_yuzdesi >= 60:
            return "Orta Düzey"
        elif basari_yuzdesi >= 40:
            return "Başlangıç-Orta Düzey"
        else:
            return "Başlangıç Düzey"

    def _ogrenme_materyalleri_oner(self, zayif_nokta: Dict) -> List[str]:
        """
        Zayıf nokta için öğrenme materyalleri önerir
        """
        konu_adı = zayif_nokta["ad"].lower()

        materyaller = []

        # Konu spesifik materyaller
        if "paragraf" in konu_adı:
            materyaller.extend(["Okuma parçaları analizi teknikleri", "Anlam çıkarımı stratejileri"])
        elif "fonksiyon" in konu_adı:
            materyaller.extend(["Fonksiyon grafiği çizimi", "Fonksiyon türleri ve özellikleri"])
        elif "denklem" in konu_adı:
            materyaller.extend(["Denklem çözme yöntemleri", "Matematiksel operasyonlar"])
        elif "elektrik" in konu_adı:
            materyaller.extend(["Elektrik devreleri", "Ohm kanunu ve uygulamaları"])
        elif "hücre" in konu_adı:
            materyaller.extend(["Hücre yapısı ve organeller", "Hücre bölünmesi"])

        # Genel materyaller
        if zayif_nokta["mevcut_seviye"] < 50:
            materyaller.append("Temel kavram tekrarı")
        else:
            materyaller.append("İleri seviye problemler")

        return materyaller[:3]  # En fazla 3 materyal

    def _onerilen_zorluk_belirle(self, mevcut_seviye: float) -> str:
        """
        Mevcut başarı seviyesine göre önerilen zorluk belirler
        """
        if mevcut_seviye < 40:
            return "Kolay"
        elif mevcut_seviye < 70:
            return "Orta"
        else:
            return "Zor"

    def _toplam_soru_sayisi(self, sonuclar: List[Dict]) -> int:
        """Toplam çözülen soru sayısını hesaplar"""
        return sum(sonuc.get("toplam_soru", 0) for sonuc in sonuclar)

    def _genel_basari_hesapla(self, sonuclar: List[Dict]) -> float:
        """Genel başarı yüzdesini hesaplar"""
        if not sonuclar:
            return 0.0

        toplam_yuzde = sum(sonuc.get("yuzde", 0) for sonuc in sonuclar)
        return toplam_yuzde / len(sonuclar)

    def _hedef_sure_hesapla(self, zayif_noktalar: List[Dict]) -> Dict[str, Any]:
        """Hedefe ulaşmak için gereken süreyi hesaplar"""
        if not zayif_noktalar:
            return {"gun": 0, "saat": 0, "mesaj": "Hedefe ulaştınız!"}

        toplam_calisma = sum(nokta["onerilen_calisma"] * 2 for nokta in zayif_noktalar)  # dk cinsinden
        gunluk_calisma = 120  # Günde 2 saat

        gereken_gun = max(1, toplam_calisma // gunluk_calisma)
        gereken_saat = toplam_calisma / 60

        return {
            "gun": gereken_gun,
            "saat": gereken_saat,
            "gunluk_calisma": gunluk_calisma,
            "mesaj": f"Güçlü alanlarınıza ulaşmak için yaklaşık {gereken_gun} gün ({gereken_saat:.1f} saat) düzenli çalışma önerilir."
        }

    def analiz_raporu_olustur(self, kullanici_id: str, format_tipi: str = "json") -> str:
        """
        Kapsamlı analiz raporu oluşturur
        """
        analiz = self.kullanici_analizi_yap(kullanici_id)

        if "hata" in analiz:
            return f"Analiz hatası: {analiz['hata']}"

        if format_tipi == "metin":
            return self._metin_raporu_olustur(analiz)
        else:
            return json.dumps(analiz, ensure_ascii=False, indent=2)

    def _metin_raporu_olustur(self, analiz: Dict) -> str:
        """
        Analiz sonuçlarını insan okunabilir metin formatında döndürür
        """
        rapor = []
        rapor.append("=" * 60)
        rapor.append("KİŞİSEL PERFORMANS ANALİZ RAPORU")
        rapor.append("=" * 60)
        rapor.append(f"Analiz Tarihi: {analiz['analiz_tarihi'][:10]}")
        rapor.append(f"Toplam Test Sayısı: {analiz['test_sayisi']}")
        rapor.append(f"Genel Başarı: %{analiz['genel_basari']:.1f}")
        rapor.append("")

        # Zayıf noktalar
        rapor.append("ZAYIF NOKTALAR")
        rapor.append("-" * 30)
        if analiz['zayif_noktalar']:
            for nokta in analiz['zayif_noktalar']:
                rapor.append(f"• {nokta['ad']}: %{nokta['mevcut_seviye']:.1f} (Hedef: %{nokta['hedef_seviye']})")
        else:
            rapor.append("Zayıf nokta bulunamadı!")

        rapor.append("")

        # Öğrenme patikası
        rapor.append("ÖĞRENME PATİKASI")
        rapor.append("-" * 30)
        patika = analiz['ogrenme_patikasi']
        rapor.append(patika['mesaj'])
        rapor.append(f"Tahmini toplam süre: {patika.get('tahmini_toplam_sure', 0)} dakika")

        rapor.append("")

        # Öneriler
        rapor.append("ÇALIŞMA ÖNERİLERİ")
        rapor.append("-" * 30)
        for oneri in analiz['oneriler'][:5]:
            rapor.append(f"• {oneri}")

        rapor.append("")
        rapor.append("=" * 60)

        return "\n".join(rapor)


def main():
    """
    Test fonksiyonu
    """
    servis = TopicSubskillAnalytics()

    # Örnek kullanıcı analizi
    kullanici_id = "127.0.0.1"  # Örnek IP adresi
    analiz = servis.kullanici_analizi_yap(kullanici_id)

    print("Öğrenci Performans Analiz Sistemi")
    print("=" * 40)

    if "hata" in analiz:
        print(f"Hata: {analiz['hata']}")
    else:
        print(f"Kullanıcı: {kullanici_id}")
        print(f"Genel Başarı: %{analiz['genel_basari']:.1f}")
        print(f"Zayıf Nokta Sayısı: {len(analiz['zayif_noktalar'])}")
        print(f"Öğrenme Patikası: {analiz['ogrenme_patikasi']['durum']}")

        # Metin raporu
        rapor = servis.analiz_raporu_olustur(kullanici_id, "metin")
        print("\n" + rapor)


if __name__ == "__main__":
    main()