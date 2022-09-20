
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
                                                                     'display_rank')
    return Response(
        {username: { 'points': points,
                     'performance_points': performance_points,
                     'rank': rank,
                    } 
        for username, points, performance_points, rank in queryset})
