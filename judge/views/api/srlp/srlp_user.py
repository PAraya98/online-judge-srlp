from dmoj import settings
from judge.models import ContestParticipation, ContestTag, Problem, Profile, Rating, Submission

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
import json 
from munch import DefaultMunch
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
def get_ranking(request):
    queryset = Profile.objects.filter(is_unlisted=False).values_list('user__username', 'points', 'performance_points',
                                                                     'display_rank', 'problem_count', 'last_access')
    return Response(
        {username: {    'points': points, #TODO: Ver diferencia entre points y performance_points 
                        'problem_count': problem_count,
                        'performance_points': performance_points,
                        'last_access': last_access,
                        'rank': rank,
                    } 
        for username, points, performance_points, rank, problem_count, last_access in queryset})
