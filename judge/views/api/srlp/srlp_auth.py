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
from judge.views.api.srlp.utils_srlp_api import get_jwt_user

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
                'access_token': str(AccessToken.for_user(user))
                #'status': 200
            })
        else:
            return Response({
                'error': "El usuario no existe"
            })
    except NameError:
        return Response({'error': NameError})

@api_view(['POST'])
def register(request):
    try:
        data = DefaultMunch.fromDict(json.loads(request.body))
        #Creación de instanicia User
        user = User.objects.create(username=data.username, email=data.username+"@SRLP_DICI.com")
        User.set_password(user, data.password)

        if(data.rol == "Administrador"):
            user.is_superuser = True
            user.is_staff = True
        elif(data.rol == "Profesor"):
            user.is_staff = True
        #if(data.rol == "Alumno"):
        
        user.first_name = data.nombre
        user.last_name = data.apellidos

        user.save()
        #Creación de instancia profile
        profile = Profile.objects.create(user=user) 

        profile.display_rank = "Alumno"
        if(data.rol == "Administrador"):
            profile.display_rank = "Administrador"
        elif(data.rol == "Profesor"):
            profile.display_rank = "Profesor"
        elif(data.rol == "Alumno"):
            profile.display_rank = "Alumno"
        elif(data.rol == "Invitado"):
            profile.display_rank = "Invitado"
        
        profile.timezone = 'America/Santiago'
        profile.organizations.add(Organization.objects.get(id=1))
        profile.save()

        return Response({   
            'avatar_url': gravatar_username(user.username),
            'refresh_token': str(RefreshToken.for_user(user)),
            'access_token': str(AccessToken.for_user(user))
        })


        
    except NameError:
        return Response({'error': NameError})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def validate_session(request):
    user = get_jwt_user(request)
    return Response(
        {'session': {   'username': user.username,
                        'gravatar': gravatar_username(user.username),
                        'is_admin': user.is_superuser,
                        'is_profesor': user.is_staff,
                        "is_logged_in": True
                    }
        })

