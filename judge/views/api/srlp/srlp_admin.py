
from dmoj import settings
from judge.jinja2.gravatar import gravatar_username
from judge.models import ContestParticipation, ContestTag, Problem, Profile, Rating, Submission, Organization
from django.db.models import F
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
import json 
from munch import DefaultMunch
from django.shortcuts import get_object_or_404

from judge.views.api.srlp.srlp_utils_api import CustomPagination, isLogueado, IsAdministrador, filter_if_not_none


@api_view(['GET'])
@permission_classes([IsAdministrador])
def get_users_info(request):    

    queryset = Profile.objects.annotate(
        username=F('user__username'), 
        nombre=F('user__first_name'),
        apellidos=F('user__last_name'),
        rol=F('display_rank'),
        email=F('user__email'))

    if(request.GET.get('order_by') is not None and request.GET.get('order_by') is not ""): queryset = queryset.order_by(request.GET.get('order_by'))

    queryset = filter_if_not_none(
        queryset,
        username__icontains=request.GET.get('username'),
        nombre__icontains=request.GET.get('nombre'),
        apellidos__icontains=request.GET.get('apellidos'),
        rol=request.GET.get('rank')
    )
    
    queryset = queryset.values('username', 'email', 'nombre', 'apellidos', 'last_access', 'rol')

    if len(queryset)> 0:
        paginator = CustomPagination()
        result_page = DefaultMunch.fromDict(paginator.paginate_queryset(queryset, request))
        array = []       
        for res in result_page:
            user = User.objects.filter(id=res.user_id).first()
            array.append({  'username': res.username,
                            'email': res.email,
                            'Nombre':  res.nombre, 
                            'Apellidos': res.apellidos,
                            'avatar_url': gravatar_username(res.username),
                            'last_access': res.last_access,
                            'rol': res.rol,
                            'active': user.is_active
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
        'rol': profile.display_rank,
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
       
        profile = get_object_or_404(Profile, user__username=data.old_username)
        if(data.rol == "Administrador"):
            profile.display_rank = "Administrador"
        elif(data.rol == "Profesor"):
            profile.display_rank = "Profesor"
        elif(data.rol == "Alumno"):
            profile.display_rank = "Alumno"
        elif(data.rol == "Invitado"):
            profile.display_rank = "Invitado"        
        
        user = User.objects.get(username=data.old_username)
        user.active = data.active
        if(data.password != ""): User.set_password(user, data.password)        
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
        user.save()
        profile.save()
        return Response({'status': True})
    except BaseException as error:
        print('An exception occurred: {}'.format(error))
        return Response({'status': False})