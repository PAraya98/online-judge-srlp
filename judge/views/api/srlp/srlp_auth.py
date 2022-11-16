from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
from judge.models import (
    Language, Organization, Profile
)
import json 
from munch import DefaultMunch
from rest_framework.permissions import IsAuthenticated
from judge.jinja2.gravatar import gravatar_username
from judge.views.api.srlp.srlp_utils_api import get_jwt_user

@api_view(['POST'])
def get_tokens_for_user(request):
    try:
        data = DefaultMunch.fromDict(json.loads(request.body))
        user = User.objects.get(username=data.username)
        if(User.check_password(user, data.password)):
            return Response({
                'username':   user.username,
                'avatar_url': gravatar_username(user.username),
                'refresh_token': str(RefreshToken.for_user(user)),
                'access_token': str(AccessToken.for_user(user)),
                'status': True
            })
        else:
            return Response({
                'error': "El usuario no existe o se encuentra deshabilitado.",
                'status': False
            })
    except NameError:
        return Response({'error': NameError})

@api_view(['GET'])
def validate_session(request):
    user = get_jwt_user(request)
    if user:
        return Response(
            {'session': {   'username': user.username,
                            'gravatar': gravatar_username(user.username),
                            'is_admin': user.is_superuser,
                            'is_profesor': user.is_staff,
                            "is_logged_in": True
                        },
                'status': True
            })
    else: return Response({'status': False, 'message': 'Sesión inválida.'})