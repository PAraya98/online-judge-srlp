
from dmoj import settings
from judge.jinja2.gravatar import gravatar_username
from judge.models import ContestParticipation, ContestTag, Problem, Profile, Rating, Submission

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
import json 
from munch import DefaultMunch
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from judge.views.api.srlp.utils_srlp_api import CustomPagination


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_users_info(request):    
    queryset = Profile.objects
    queryset = queryset.values_list('user__username', 'display_rank', 'last_access').order_by('user__username')
    
    if len(queryset)> 0:
        paginator = CustomPagination()
        result_page = paginator.paginate_queryset(queryset, request)
        array = []
        for username, rank, last_access in result_page:
            array.append({  'username': username,
                            'avatar_url': gravatar_username(username),
                            'last_access': last_access,
                            'rank': rank,
                        })        
        return Response(data={'usuarios': "xd"})
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
