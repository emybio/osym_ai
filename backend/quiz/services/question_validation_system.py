import logging
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import re
import xml.etree.ElementTree as ET
from sympy import sympify, lambdify, symbols
import numpy as np

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REGENERATION = "needs_regeneration"


class ValidationErrorType(Enum):
    SVG_PARSE_ERROR = "svg_parse_error"
    MATH_INCONSISTENCY = "math_inconsistency"
    GEOMETRY_ANGLE_MISMATCH = "geometry_angle_mismatch"
    PARABOLA_POINT_MISMATCH = "parabola_point_mismatch"
    MISSING_VISUAL_ELEMENTS = "missing_visual_elements"
    TEXT_VISUAL_MISMATCH = "text_visual_mismatch"
    CHOICE_INCONSISTENCY = "choice_inconsistency"


@dataclass
class ValidationResult:
    status: ValidationStatus
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error_type: ValidationErrorType, message: str, details: Dict = None):
        self.errors.append({
            'type': error_type.value,
            'message': message,
            'details': details or {}
        })
        self.score -= 20
        
    def add_warning(self, message: str):
        self.warnings.append(message)
        self.score -= 5
        
    def is_valid(self) -> bool:
        return self.status == ValidationStatus.PASSED and self.score >= 60


class QuestionValidationSystem:
    """
    Soru oluşturma sürecinde çok katmanlı doğrulama yapan sistem.
    
    Doğrulama Akışı:
    1. Soru Oluştur (AI)
    2. Temel Yapı Kontrolü
    3. SVG Doğrulama (varsa)
    4. Matematiksel Tutarlılık Kontrolü
    5. Görsel-Metin Uyum Kontrolü
    6. Seçenek Tutarlılığı Kontrolü
    7. Final Onay / Yeniden Üretim
    """
    
    def __init__(self):
        self.tolerance = 0.15
        self.max_regeneration_attempts = 3
        
    def validate_question(self, question_data: Dict, question_type: str = "general") -> ValidationResult:
        """
        Ana doğrulama fonksiyonu - tüm kontrolleri sırayla yapar
        """
        result = ValidationResult(status=ValidationStatus.VALIDATING, score=100.0)
        
        try:
            # 1. Temel yapı kontrolü
            self._validate_basic_structure(question_data, result)
            
            # 2. Soru tipine göre özel doğrulama
            if question_type == "parabola":
                self._validate_parabola_question(question_data, result)
            elif question_type == "geometry":
                self._validate_geometry_question(question_data, result)
            elif question_type == "function_graph":
                self._validate_function_graph(question_data, result)
            
            # 3. SVG varsa doğrula
            if question_data.get('image_svg'):
                self._validate_svg_content(question_data, result)
            
            # 4. Seçenek tutarlılığı
            self._validate_choices(question_data, result)
            
            # 5. Final durum belirleme
            if result.score >= 80:
                result.status = ValidationStatus.PASSED
            elif result.score >= 60:
                result.status = ValidationStatus.PASSED
                result.add_warning("Soru geçti ama bazı iyileştirmeler yapılabilir")
            else:
                result.status = ValidationStatus.FAILED
                
        except Exception as e:
            logger.error(f"Validation error: {e}")
            result.add_error(ValidationErrorType.SVG_PARSE_ERROR, str(e))
            result.status = ValidationStatus.FAILED
            
        return result
    
    def _validate_basic_structure(self, question_data: Dict, result: ValidationResult):
        """Temel soru yapısını kontrol eder"""
        required_fields = ['question_text', 'choices', 'correct_answer']
        
        for field in required_fields:
            if not question_data.get(field):
                result.add_error(
                    ValidationErrorType.TEXT_VISUAL_MISMATCH,
                    f"Zorunlu alan eksik: {field}"
                )
        
        # Soru metni uzunluk kontrolü
        question_text = question_data.get('question_text', '')
        if len(question_text) < 20:
            result.add_warning("Soru metni çok kısa")
        
        # Seçenek sayısı kontrolü
        choices = question_data.get('choices', [])
        if len(choices) != 5:
            result.add_error(
                ValidationErrorType.CHOICE_INCONSISTENCY,
                f"5 seçenek olmalı, {len(choices)} seçenek bulundu"
            )
    
    def _validate_parabola_question(self, question_data: Dict, result: ValidationResult):
        """
        Parabol sorularında:
        - Fonksiyon tanımı ile görsel uyumu
        - Tepe noktası doğruluğu
        - Kök noktaları doğruluğu
        - Eksen kesişim noktaları
        """
        question_text = question_data.get('question_text', '')
        svg_content = question_data.get('image_svg', '')
        
        # Fonksiyonu metinden çıkar
        function_str = self._extract_function(question_text)
        if not function_str:
            result.add_error(
                ValidationErrorType.MATH_INCONSISTENCY,
                "Soru metninde fonksiyon tanımı bulunamadı"
            )
            return
        
        # SVG'den noktaları çıkar
        if svg_content:
            svg_points = self._extract_parabola_points_from_svg(svg_content)
            
            # Fonksiyonu hesapla
            calculated_points = self._calculate_parabola_points(function_str)
            
            # Karşılaştır
            if not self._compare_parabola_points(svg_points, calculated_points):
                result.add_error(
                    ValidationErrorType.PARABOLA_POINT_MISMATCH,
                    "SVG'deki parabol ile fonksiyon tanımı uyuşmuyor",
                    {
                        'function': function_str,
                        'svg_points_sample': svg_points[:5] if svg_points else [],
                        'calculated_points_sample': calculated_points[:5] if calculated_points else []
                    }
                )
            
            # Tepe noktası kontrolü
            vertex = self._find_vertex(function_str)
            svg_vertex = self._find_svg_vertex(svg_points)
            
            if vertex and svg_vertex:
                distance = np.sqrt((vertex[0] - svg_vertex[0])**2 + (vertex[1] - svg_vertex[1])**2)
                if distance > self.tolerance * 10:
                    result.add_error(
                        ValidationErrorType.PARABOLA_POINT_MISMATCH,
                        f"Tepe noktası uyuşmuyor. Hesaplanan: {vertex}, SVG: {svg_vertex}"
                    )
    
    def _validate_geometry_question(self, question_data: Dict, result: ValidationResult):
        """
        Geometri sorularında:
        - Açı işaretlerinin doğru konumda olması
        - Verilen açı değerleri ile görseldeki açıların uyumu
        - Kenar uzunlukları tutarlılığı
        """
        question_text = question_data.get('question_text', '')
        svg_content = question_data.get('image_svg', '')
        
        # Metinden açı değerlerini çıkar
        text_angles = self._extract_angles_from_text(question_text)
        
        if svg_content and text_angles:
            # SVG'den açı işaretlerini ve konumlarını çıkar
            svg_angles = self._extract_angles_from_svg(svg_content)
            
            # Açı sayısı kontrolü
            if len(text_angles) != len(svg_angles):
                result.add_warning(
                    f"Metinde {len(text_angles)} açı, görselde {len(svg_angles)} açı işareti var"
                )
            
            # Her açı için konum ve değer kontrolü
            for text_angle in text_angles:
                matching_svg_angle = self._find_matching_angle(text_angle, svg_angles)
                if not matching_svg_angle:
                    result.add_error(
                        ValidationErrorType.GEOMETRY_ANGLE_MISMATCH,
                        f"'{text_angle['label']}' açısı için uygun işaret bulunamadı"
                    )
                elif abs(text_angle['value'] - matching_svg_angle['value']) > 5:
                    result.add_error(
                        ValidationErrorType.GEOMETRY_ANGLE_MISMATCH,
                        f"Açı değeri uyuşmuyor: {text_angle['label']} = {text_angle['value']}° (metin) vs {matching_svg_angle['value']}° (görsel)"
                    )
    
    def _validate_function_graph(self, question_data: Dict, result: ValidationResult):
        """Fonksiyon grafik sorularını doğrular"""
        question_text = question_data.get('question_text', '')
        svg_content = question_data.get('image_svg', '')
        
        function_str = self._extract_function(question_text)
        if not function_str or not svg_content:
            return
        
        # Grafikteki noktaları al
        svg_points = self._parse_svg_path(svg_content)
        
        # Fonksiyondan noktalar hesapla
        calculated_points = self._calculate_function_points(function_str)
        
        # Karşılaştır
        match_score = self._compare_function_points(svg_points, calculated_points)
        
        if match_score < 0.8:
            result.add_error(
                ValidationErrorType.MATH_INCONSISTENCY,
                f"Fonksiyon grafiği tutarsız (uyum skoru: {match_score:.2f})"
            )
    
    def _validate_svg_content(self, question_data: Dict, result: ValidationResult):
        """SVG içeriğinin geçerliliğini kontrol eder"""
        svg_content = question_data.get('image_svg', '')
        
        try:
            root = ET.fromstring(svg_content)
            
            # Temel SVG elementlerini kontrol et
            if not root.tag.endswith('svg'):
                result.add_error(
                    ValidationErrorType.SVG_PARSE_ERROR,
                    "Geçersiz SVG root elementi"
                )
            
            # ViewBox kontrolü
            if not root.get('viewBox'):
                result.add_warning("SVG viewBox tanımı eksik")
            
            # En az bir görsel element olmalı
            visual_elements = root.findall('.//*')
            if len(visual_elements) < 2:
                result.add_error(
                    ValidationErrorType.MISSING_VISUAL_ELEMENTS,
                    "SVG'de yeterli görsel element yok"
                )
                
        except ET.ParseError as e:
            result.add_error(
                ValidationErrorType.SVG_PARSE_ERROR,
                f"SVG parse hatası: {str(e)}"
            )
    
    def _validate_choices(self, question_data: Dict, result: ValidationResult):
        """Seçeneklerin tutarlılığını kontrol eder"""
        choices = question_data.get('choices', [])
        correct_answer = question_data.get('correct_answer')
        
        if not choices:
            return
        
        # Boş seçenek kontrolü
        for i, choice in enumerate(choices):
            if not choice.get('text', '').strip():
                result.add_error(
                    ValidationErrorType.CHOICE_INCONSISTENCY,
                    f"Seçenek {i+1} boş"
                )
        
        # Doğru cevap kontrolü
        if correct_answer:
            correct_found = any(c.get('text') == correct_answer for c in choices)
            if not correct_found:
                result.add_error(
                    ValidationErrorType.CHOICE_INCONSISTENCY,
                    "Doğru cevap seçenekler arasında bulunamadı"
                )
        
        # Tekrar eden seçenek kontrolü
        choice_texts = [c.get('text', '').strip() for c in choices]
        if len(choice_texts) != len(set(choice_texts)):
            result.add_warning("Tekrar eden seçenekler var")
    
    # Yardımcı fonksiyonlar
    
    def _extract_function(self, text: str) -> Optional[str]:
        """Metinden matematiksel fonksiyonu çıkarır"""
        patterns = [
            r'f\(x\)\s*=\s*([^,\.\n]+)',
            r'y\s*=\s*([^,\.\n]+)',
            r'fonksiyon[ua]?\s*[:\s]+([^,\.\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                func_str = match.group(1).strip()
                func_str = func_str.replace('²', '**2').replace('³', '**3')
                func_str = func_str.replace('×', '*').replace('÷', '/')
                return func_str
        return None
    
    def _extract_parabola_points_from_svg(self, svg_content: str) -> List[Tuple[float, float]]:
        """SVG'den parabol noktalarını çıkarır"""
        return self._parse_svg_path(svg_content)
    
    def _parse_svg_path(self, svg_content: str) -> List[Tuple[float, float]]:
        """SVG path'den koordinatları çıkarır"""
        try:
            root = ET.fromstring(svg_content)
            points = []
            
            for path in root.findall('.//{http://www.w3.org/2000/svg}path'):
                d = path.get('d', '')
                coords = re.findall(r'[-+]?\d*\.?\d+', d)
                coords = [float(c) for c in coords]
                
                for i in range(0, len(coords)-1, 2):
                    points.append((coords[i], coords[i+1]))
            
            return points
        except:
            return []
    
    def _calculate_parabola_points(self, function_str: str, x_range: Tuple[float, float] = (-10, 10)) -> List[Tuple[float, float]]:
        """Fonksiyondan parabol noktalarını hesaplar"""
        try:
            x = symbols('x')
            expr = sympify(function_str)
            f = lambdify(x, expr, 'numpy')
            
            x_vals = np.linspace(x_range[0], x_range[1], 100)
            y_vals = f(x_vals)
            
            return list(zip(x_vals, y_vals))
        except:
            return []
    
    def _calculate_function_points(self, function_str: str, x_range: Tuple[float, float] = (-10, 10)) -> List[Tuple[float, float]]:
        """Genel fonksiyon noktalarını hesaplar"""
        return self._calculate_parabola_points(function_str, x_range)
    
    def _compare_parabola_points(self, svg_points: List[Tuple[float, float]], 
                                 calculated_points: List[Tuple[float, float]]) -> bool:
        """İki nokta setini karşılaştırır"""
        if not svg_points or not calculated_points:
            return False
        
        # Örnekleme yaparak karşılaştır
        sample_size = min(20, len(svg_points), len(calculated_points))
        svg_sample = svg_points[::len(svg_points)//sample_size][:sample_size]
        calc_sample = calculated_points[::len(calculated_points)//sample_size][:sample_size]
        
        matches = 0
        for svg_point in svg_sample:
            for calc_point in calc_sample:
                distance = np.sqrt((svg_point[0] - calc_point[0])**2 + (svg_point[1] - calc_point[1])**2)
                if distance < self.tolerance * 10:
                    matches += 1
                    break
        
        return matches / sample_size > 0.7
    
    def _compare_function_points(self, svg_points: List[Tuple[float, float]], 
                                calculated_points: List[Tuple[float, float]]) -> float:
        """Fonksiyon noktalarını karşılaştırıp uyum skoru döner"""
        if not svg_points or not calculated_points:
            return 0.0
        
        return 0.85 if self._compare_parabola_points(svg_points, calculated_points) else 0.5
    
    def _find_vertex(self, function_str: str) -> Optional[Tuple[float, float]]:
        """Parabolün tepe noktasını bulur"""
        try:
            x = symbols('x')
            expr = sympify(function_str)
            
            # ax^2 + bx + c formunda ise
            coeffs = [expr.coeff(x, 2), expr.coeff(x, 1), expr.coeff(x, 0)]
            a, b, c = [float(coeff) if coeff else 0 for coeff in coeffs]
            
            if a == 0:
                return None
            
            vertex_x = -b / (2 * a)
            vertex_y = a * vertex_x**2 + b * vertex_x + c
            
            return (vertex_x, vertex_y)
        except:
            return None
    
    def _find_svg_vertex(self, points: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        """SVG noktalarından tepe noktasını bulur"""
        if not points:
            return None
        
        # En yüksek veya en düşük y değerine sahip nokta
        return max(points, key=lambda p: abs(p[1]))
    
    def _extract_angles_from_text(self, text: str) -> List[Dict]:
        """Metinden açı bilgilerini çıkarır"""
        angles = []
        
        # Açı kalıpları: "∠ABC = 60°", "açı ABC = 60", "m(ABC) = 60"
        patterns = [
            r'[∠m]\(?([A-Z]{3})\)?\s*=\s*(\d+)',
            r'açı\s+([A-Z]{3})\s*=\s*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                angles.append({
                    'label': match.group(1),
                    'value': float(match.group(2))
                })
        
        return angles
    
    def _extract_angles_from_svg(self, svg_content: str) -> List[Dict]:
        """SVG'den açı işaretlerini çıkarır"""
        # Bu fonksiyon SVG'deki arc elementlerini veya açı işaretlerini analiz eder
        # Şimdilik basit bir implementasyon
        return []
    
    def _find_matching_angle(self, text_angle: Dict, svg_angles: List[Dict]) -> Optional[Dict]:
        """Metin açısına karşılık gelen SVG açısını bulur"""
        for svg_angle in svg_angles:
            if svg_angle.get('label') == text_angle.get('label'):
                return svg_angle
        return None


def generate_validation_report(result: ValidationResult) -> str:
    """Doğrulama sonucunu okunabilir rapor haline getirir"""
    report = []
    report.append("=" * 60)
    report.append("SORU DOĞRULAMA RAPORU")
    report.append("=" * 60)
    report.append(f"Durum: {result.status.value.upper()}")
    report.append(f"Skor: {result.score:.1f}/100")
    report.append("")
    
    if result.errors:
        report.append("HATALAR:")
        for i, error in enumerate(result.errors, 1):
            report.append(f"{i}. [{error['type']}] {error['message']}")
            if error.get('details'):
                report.append(f"   Detaylar: {error['details']}")
        report.append("")
    
    if result.warnings:
        report.append("UYARILAR:")
        for i, warning in enumerate(result.warnings, 1):
            report.append(f"{i}. {warning}")
        report.append("")
    
    report.append("=" * 60)
    
    return "\n".join(report)
