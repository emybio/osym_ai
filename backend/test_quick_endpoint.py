#!/usr/bin/env python
import os
import sys
import django

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osym_ai.settings')
sys.path.append('/mnt/c/Users/kur06/Downloads/osym_ai/backend')
django.setup()

from django.urls import reverse
from quiz.views import init_temp_exam

def test_endpoint():
    print("Testing Quick Test Endpoint...")

    # Test reverse URL
    try:
        url = reverse('init-temp-exam')
        print(f"✅ Reverse URL works: {url}")
    except Exception as e:
        print(f"❌ Reverse URL failed: {e}")
        return

    # Test view import
    try:
        print("✅ init_temp_exam view imported successfully")
        print(f"View function: {init_temp_exam}")
    except Exception as e:
        print(f"❌ View import failed: {e}")
        return

    print("\n✅ All tests passed!")
    print("If endpoints still return 404, check:")
    print("1. Browser URL: http://localhost:8000/api/v1/quiz/quicktest/init/")
    print("2. Django debug settings")
    print("3. CSRF middleware issues")

if __name__ == "__main__":
    test_endpoint()