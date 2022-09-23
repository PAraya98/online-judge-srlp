from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from judge.models import (
    Language, Organization, Profile
)
import json 
from munch import DefaultMunch
from rest_framework.permissions import IsAuthenticated
from judge.jinja2.gravatar import gravatar_username

@api_view(['POST'])
def get_tokens_for_user(request):
    try:
        data = DefaultMunch.fromDict(json.loads(request.body))
        user = User.objects.get(username=data.username)
        if(User.check_password(user, data.password)):
            return Response({
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
        user = User.objects.create(username=data.username, email=data.email)
        User.set_password(user, data.password)
        user.save()

        profile = Profile.objects.create(
            user=user     
        ) 
        profile.timezone = 'America/Toronto'
        profile.organizations.add(Organization.objects.get(id=1))
        profile.save()

        return Response({   
            'avatar_url': gravatar_username(user.username),
            'refresh_token': str(RefreshToken.for_user(user)),
            'access_token': str(AccessToken.for_user(user))
        })
        
    except NameError:
        return Response({'error': NameError})

@api_view(['POST'])
def validation(request):
    permission_classes = (IsAuthenticated)
    #request.user = JWTAuthentication().authenticate(request)[0]
    return Response({'Validadon': True})