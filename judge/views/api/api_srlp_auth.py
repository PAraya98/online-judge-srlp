from operator import attrgetter
from django.conf import settings
from django.utils.encoding import force_bytes
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db.models import Count, F, OuterRef, Prefetch, Q, Subquery
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import BaseListView
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.contrib.auth.models import User

from judge.models import (
    Language, Organization, Profile
)
import json 
from munch import DefaultMunch

@api_view(['POST'])
def get_tokens_for_user(request):
    try:
        data = DefaultMunch.fromDict(json.loads(request.body))
        user = User.objects.get(username=data.username)
        if(User.check_password(user, data.password)):
            return Response({
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
            'refresh_token': str(RefreshToken.for_user(user)),
            'access_token': str(AccessToken.for_user(user))
        })
        
    except NameError:
        return Response({'error': NameError})

@api_view(['POST'])
class clase_prueba:
    def __init__(self, request):
        self.request = request

    def jwt_validation(self):
        try:
            print(self.request)
            return Response({ "a": JWTAuthentication.authenticate(self, self.request)})
        except NameError:
            return Response({'error': NameError})

    

