import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """Login endpoint for admin users"""
    try:
        data = request.data
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return Response(
                {"error": "Kullanıcı adı ve şifre gereklidir"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Check if user is staff
            if not user.is_staff:
                return Response(
                    {"error": "Bu sisteme sadece admin kullanıcıları erişebilir"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Login the user
            login(request, user)

            return Response({
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser
                },
                "message": "Giriş başarılı"
            })

        else:
            return Response(
                {"error": "Kullanıcı adı veya şifre hatalı"},
                status=status.HTTP_401_UNAUTHORIZED
            )

    except Exception as e:
        logger.error(f"Login error: {e}")
        return Response(
            {"error": "Giriş işlemi başarısız"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
def logout_view(request):
    """Logout endpoint"""
    try:
        logout(request)
        return Response({
            "success": True,
            "message": "Çıkış başarılı"
        })
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return Response(
            {"error": "Çıkış işlemi başarısız"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
def user_profile(request):
    """Get current user profile"""
    try:
        if not request.user.is_authenticated:
            return Response(
                {"error": "Oturum açılmamış"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response({
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "is_staff": request.user.is_staff,
                "is_superuser": request.user.is_superuser
            }
        })

    except Exception as e:
        logger.error(f"Profile error: {e}")
        return Response(
            {"error": "Profil bilgileri alınamadı"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_csrf_token(request):
    """Get CSRF token for frontend"""
    from django.middleware.csrf import get_token
    token = get_token(request)
    return Response({"csrfToken": token})


@api_view(["GET"])
@permission_classes([AllowAny])
def check_auth(request):
    """Check if user is authenticated and has admin privileges"""
    try:
        if not request.user.is_authenticated:
            return Response({
                "authenticated": False,
                "is_admin": False,
                "message": "Oturum açılmamış"
            })

        return Response({
            "authenticated": True,
            "is_admin": request.user.is_staff,
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "is_staff": request.user.is_staff,
                "is_superuser": request.user.is_superuser
            }
        })

    except Exception as e:
        logger.error(f"Auth check error: {e}")
        return Response(
            {"authenticated": False, "is_admin": False},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )