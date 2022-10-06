
from dmoj import settings
from judge.jinja2.gravatar import gravatar_username
from judge.models import ContestParticipation, ContestTag, Problem, Profile, Rating, Submission, Organization

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
import json 
from munch import DefaultMunch
from django.shortcuts import get_object_or_404

from judge.views.api.srlp.utils_srlp_api import CustomPagination, isLogueado, IsAdministrador


@api_view(['GET'])
@permission_classes([IsAdministrador])
def get_users_info(request):    
    queryset = Profile.objects
    queryset = queryset.values_list('user__username', 'user__first_name', 'user__last_name', 
    'user__email', 'display_rank', 'last_access').order_by('user__username')
    
    if len(queryset)> 0:
        paginator = CustomPagination()
        result_page = paginator.paginate_queryset(queryset, request)
        array = []
        for username, nombre, apellidos, email, rank, last_access in result_page:
            array.append({  'username': username,
                            'email': email,
                            'Nombre':  nombre, 
                            'Apellidos': apellidos,
                            'avatar_url': gravatar_username(username),
                            'last_access': last_access,
                            'rank': rank,
                        })        
        data = {'usuarios':  array}
        return paginator.get_paginated_response(data)
    else:
        return Response({})
        

#Obtener información del alumno
@api_view(['GET'])
@permission_classes([IsAdministrador])
def get_user_data(request):
    code = request.GET.getlist('username')
    username = '' if not code else code[0]
    profile = get_object_or_404(Profile, user__username=username)
    submissions = list(Submission.objects.filter(case_points=F('case_total'), user=profile, problem__is_public=True,
                                                 problem__is_organization_private=False)
                       .values('problem').distinct().values_list('problem__code', flat=True))
    user = User.objects.get(username=username)
    
    resp = {
        'username': user.username,
        'about': profile.about,
        'points': profile.points,
        'performance_points': profile.performance_points,
        'rank': profile.display_rank,
        'solved_problems': submissions,
        'organizations': list(profile.organizations.values_list('id', flat=True)),
    }

    return Response(resp)

@api_view(['POST'])
@permission_classes([IsAdministrador])
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
        user.last_name = data.apellido_paterno + " " + data.apellido_materno
        user.save()
        #Creación de instancia profile
        profile = Profile.objects.create(user=user) 
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
        return Response({'status': True})
    except BaseException as error:
        print('An exception occurred: {}'.format(error))
        return Response({'status': False})


@api_view(['POST'])
@permission_classes([IsAdministrador])
def modify_user(request):
    try:
        data = DefaultMunch.fromDict(json.loads(request.body))
        user = get_object_or_404(Profile, user=data.username)      
        User.set_password(user, data.password)
        user.first_name = data.nombre
        user.last_name = data.apellidos
        if(data.rol == "Administrador"):
            user.is_superuser = True
            user.is_staff = True
        elif(data.rol == "Profesor"):
            user.is_staff = True
        #if(data.rol == "Alumno"):
        user.first_name = data.nombre
        user.last_name = data.apellido_paterno + " " + data.apellido_materno
        user.username = data.username
        profile = get_object_or_404(Profile, user__username=data.username)
        if(data.rol == "Administrador"):
            profile.display_rank = "Administrador"
        elif(data.rol == "Profesor"):
            profile.display_rank = "Profesor"
        elif(data.rol == "Alumno"):
            profile.display_rank = "Alumno"
        elif(data.rol == "Invitado"):
            profile.display_rank = "Invitado"
        user.save()
        profile.save()
    except Exception as e:
        print("Error: ")
        return Response({'status': False})


