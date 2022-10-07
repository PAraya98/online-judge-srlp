from rest_framework.response import Response
from collections import OrderedDict, namedtuple
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import permissions
from judge.models import Profile
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view

def get_jwt_user(request):
    user = JWTAuthentication().authenticate(request)
    return None if user is None else user[0]

def acces_denied(bool_list):
    return Response({'status': "Acceso denegado"})

def filter_if_not_none(qs, **kwargs):
    return qs.filter(**{k: v for k, v in kwargs.items() if v is not None})

class CustomPagination(PageNumberPagination):
    '''
    Paginación para querys:
    Para utilizar se tienen que agregar los parametros ?page=2&page_size=3,
    Donde p es la página y page_size la cantidad de datos a mostrar
    '''
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

    

    def get_paginated_response(self, data):
        data['page_number'] = self.page.number
        return Response(data)


######################################################
#PERMISOS DE USUARIO


class isLogueado(IsAuthenticated):
    pass

class IsAdministrador(permissions.BasePermission):
    def has_permission(self, request, view):
        if(bool(request.user and request.user.is_authenticated)):
            return bool(request.user.is_superuser)
        else: return False

class isProfesor(permissions.BasePermission):
    def has_permission(self, request, view):
        if(bool(request.user and request.user.is_authenticated)):
            return bool(request.user.staff)
        else: return False

class isAlumno(permissions.BasePermission):
    def has_permission(self, request, view):
        if(bool(request.user and request.user.is_authenticated)):
            profile = get_object_or_404(Profile, user__username=request.user.username)
            return bool(profile.display_rank == "Alumno")
        else: return False

class isVisitante(permissions.BasePermission):
    def has_permission(self, request, view):
        if(bool(request.user and request.user.is_authenticated)):
            profile = get_object_or_404(Profile, user__username=request.user.username)
            return bool(profile.display_rank == "Visitante")
        else: return False