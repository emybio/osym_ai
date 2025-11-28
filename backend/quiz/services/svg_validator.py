import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional
import numpy as np
from sympy import sympify, lambdify, symbols
import logging

logger = logging.getLogger(__name__)


class SVGValidationError(Exception):
    """SVG validation error"""
    pass


class SVGValidator:
    """
    SVG içeriğini parse edip matematiksel doğruluğunu kontrol eder.
    """
    
    def __init__(self):
        self.tolerance = 0.1  # %10 tolerans
        
    def extract_function_from_text(self, question_text: str) -> Optional[str]:
        """
        Soru metninden matematiksel fonksiyonu çıkarır.
        Örnek: "f(x) = x² - 4x + 3" → "x**2 - 4*x + 3"
        """
        patterns = [
            r'f\(x\)\s*=\s*([^,\.\n]+)',
            r'y\s*=\s*([^,\.\n]+)',
            r'fonksiyon[ua]?\s*[:\s]+([^,\.\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question_text, re.IGNORECASE)
            if match:
                func_str = match.group(1).strip()
                # Türkçe karakterleri dönüştür
                func_str = func_str.replace('²', '**2').replace('³', '**3')
                func_str = func_str.replace('×', '*').replace('÷', '/')
                return func_str
        return None
    
    def parse_svg_path(self, svg_content: str) -> List[Tuple[float, float]]:
        """
        SVG path elementinden koordinatları çıkarır.
        """
        try:
            root = ET.fromstring(svg_content)
            points = []
            
            # Path elementlerini bul
            for path in root.findall('.//{http://www.w3.org/2000/svg}path'):
                d = path.get('d', '')
                # Basit path parsing (M, L, Q, C komutları)
                coords = re.findall(r'[-+]?\d*\.?\d+', d)
                coords = [float(c) for c in coords]
                
                # Koordinatları (x, y) çiftleri olarak grupla
                for i in range(0, len(coords)-1, 2):
                    points.append((coords[i], coords[i+1]))
            
            # Polyline ve polygon elementleri
            for elem in root.findall('.//{http://www.w3.org/2000/svg}polyline') + \
                        root.findall('.//{http://www.w3.org/2000/svg}polygon'):
                points_str = elem.get('points', '')
                coords = re.findall(r'[-+]?\d*\.?\d+', points_str)
                coords = [float(c) for c in coords]
                
                for i in range(0, len(coords)-1, 2):
                    points.append((coords[i], coords[i+1]))
            
            return points
        except Exception as e:
            logger.error(f"SVG parsing error: {e}")
            return []
    
    def extract_viewbox(self, svg_content: str) -> Tuple[float, float, float, float]:
        """
        SVG viewBox değerlerini çıkarır.
        Returns: (min_x, min_y, width, height)
        """
        try:
            root = ET.fromstring(svg_content)
            viewbox = root.get('viewBox', '0 0 400 300')
            values = [float(v) for v in viewbox.split()]
            return tuple(values)
        except:
            return (0, 0, 400, 300)
    
    def svg_to_cartesian(self, svg_points: List[Tuple[float, float]], 
                         viewbox: Tuple[float, float, float, float],
                         x_range: Tuple[float, float] = (-10, 10),
                         y_range: Tuple[float, float] = (-10, 10)) -> List[Tuple[float, float]]:
        """
        SVG koordinatlarını Kartezyen koordinatlara dönüştürür.
        SVG: (0,0) sol üst köşe, y aşağı doğru artar
        Kartezyen: (0,0) merkez, y yukarı doğru artar
        """
        min_x, min_y, width, height = viewbox
        x_min, x_max = x_range
        y_min, y_max = y_range
        
        cartesian_points = []
        for svg_x, svg_y in svg_points:
            # SVG'den normalize et (0-1 arası)
            norm_x = (svg_x - min_x) / width
            norm_y = (svg_y - min_y) / height
            
            # Kartezyen koordinatlara dönüştür
            cart_x = x_min + norm_x * (x_max - x_min)
            cart_y = y_max - norm_y * (y_max - y_min)  # Y eksenini ters çevir
            
            cartesian_points.append((cart_x, cart_y))
        
        return cartesian_points
    
    def validate_function_match(self, function_str: str, 
                                svg_points: List[Tuple[float, float]],
                                tolerance: float = None) -> Dict:
        """
        Fonksiyon ile SVG noktalarının uyumunu kontrol eder.
        """
        if tolerance is None:
            tolerance = self.tolerance
            
        try:
            # Fonksiyonu sympy ile parse et
            x = symbols('x')
            expr = sympify(function_str)
            func = lambdify(x, expr, 'numpy')
            
            # Her SVG noktası için fonksiyon değerini hesapla
            errors = []
            valid_points = 0
            
            for svg_x, svg_y in svg_points:
                try:
                    expected_y = float(func(svg_x))
                    error = abs(expected_y - svg_y)
                    relative_error = error / (abs(expected_y) + 1e-10)
                    
                    errors.append({
                        'x': svg_x,
                        'svg_y': svg_y,
                        'expected_y': expected_y,
                        'error': error,
                        'relative_error': relative_error
                    })
                    
                    if relative_error <= tolerance:
                        valid_points += 1
                except:
                    continue
            
            if not errors:
                return {
                    'valid': False,
                    'reason': 'No valid points to compare',
                    'accuracy': 0.0
                }
            
            accuracy = valid_points / len(errors)
            avg_error = np.mean([e['relative_error'] for e in errors])
            
            return {
                'valid': accuracy >= 0.8,  # En az %80 doğruluk
                'accuracy': accuracy,
                'average_error': avg_error,
                'total_points': len(errors),
                'valid_points': valid_points,
                'errors': errors[:5]  # İlk 5 hata
            }
            
        except Exception as e:
            logger.error(f"Function validation error: {e}")
            return {
                'valid': False,
                'reason': f'Validation error: {str(e)}',
                'accuracy': 0.0
            }
    
    def validate_question(self, question_text: str, svg_content: str) -> Dict:
        """
        Soru metni ve SVG içeriğini tam olarak doğrular.
        """
        result = {
            'valid': False,
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        # 1. Fonksiyonu çıkar
        function_str = self.extract_function_from_text(question_text)
        if not function_str:
            result['errors'].append('Soru metninde fonksiyon bulunamadı')
            return result
        
        result['checks']['function_extracted'] = True
        result['function'] = function_str
        
        # 2. SVG'yi parse et
        svg_points = self.parse_svg_path(svg_content)
        if not svg_points:
            result['errors'].append('SVG içinde grafik noktaları bulunamadı')
            return result
        
        result['checks']['svg_parsed'] = True
        result['svg_points_count'] = len(svg_points)
        
        # 3. ViewBox'ı al
        viewbox = self.extract_viewbox(svg_content)
        result['viewbox'] = viewbox
        
        # 4. Koordinat dönüşümü
        cartesian_points = self.svg_to_cartesian(svg_points, viewbox)
        result['checks']['coordinates_converted'] = True
        
        # 5. Matematiksel doğrulama
        validation = self.validate_function_match(function_str, cartesian_points)
        result['validation'] = validation
        result['valid'] = validation['valid']
        
        # 6. Uyarılar
        if validation['accuracy'] < 0.9:
            result['warnings'].append(f"Grafik doğruluğu düşük: %{validation['accuracy']*100:.1f}")
        
        if len(svg_points) < 10:
            result['warnings'].append(f"Çok az nokta: {len(svg_points)} (minimum 10 önerilir)")
        
        return result


class AIValidatorService:
    """
    AI kullanarak soru kalitesini doğrular (Multi-Agent yaklaşımı)
    """
    
    def __init__(self, ai_service):
        self.ai_service = ai_service
        self.svg_validator = SVGValidator()
    
    def validate_with_ai(self, question_data: Dict) -> Dict:
        """
        AI ile soru kalitesini kontrol eder.
        """
        validation_prompt = f"""
Sen bir matematik soru doğrulama uzmanısın. Aşağıdaki soruyu incele:

SORU: {question_data.get('question_text', '')}

FONKSIYON: {question_data.get('function', 'Belirtilmemiş')}

SEÇENEKLER:
{self._format_choices(question_data.get('choices', {}))}

DOĞRU CEVAP: {question_data.get('correct_answer', '')}

KONTROL ET:
1. Fonksiyon matematiksel olarak doğru mu?
2. Seçeneklerdeki değerler fonksiyonun kökleri mi?
3. Doğru cevap gerçekten doğru mu?
4. Soru pedagojik olarak uygun mu?
5. Yanıltıcı seçenekler mantıklı mı?

JSON formatında döndür:
{{
    "is_valid": true/false,
    "mathematical_correctness": "açıklama",
    "pedagogical_quality": "açıklama",
    "issues": ["sorun1", "sorun2"],
    "suggestions": ["öneri1", "öneri2"],
    "confidence_score": 0.0-1.0
}}
"""
        
        try:
            messages = [
                {"role": "system", "content": "Sen bir matematik eğitimi uzmanısın."},
                {"role": "user", "content": validation_prompt}
            ]
            
            response = self.ai_service._get_openai_response(messages, json_mode=True)
            import json
            validation_result = json.loads(response.choices[0].message.content)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"AI validation error: {e}")
            return {
                'is_valid': False,
                'error': str(e)
            }
    
    def _format_choices(self, choices: Dict) -> str:
        """Seçenekleri formatlar"""
        return '\n'.join([f"{k}) {v}" for k, v in choices.items()])
    
    def full_validation(self, question_text: str, svg_content: str, 
                       choices: Dict, correct_answer: str) -> Dict:
        """
        Tam doğrulama: SVG + AI
        """
        # 1. SVG Matematiksel Doğrulama
        svg_validation = self.svg_validator.validate_question(question_text, svg_content)
        
        # 2. AI Doğrulama
        question_data = {
            'question_text': question_text,
            'function': svg_validation.get('function'),
            'choices': choices,
            'correct_answer': correct_answer
        }
        ai_validation = self.validate_with_ai(question_data)
        
        # 3. Sonuçları birleştir
        return {
            'overall_valid': svg_validation['valid'] and ai_validation.get('is_valid', False),
            'svg_validation': svg_validation,
            'ai_validation': ai_validation,
            'confidence': ai_validation.get('confidence_score', 0.0),
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
