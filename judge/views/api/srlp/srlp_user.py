from dmoj import settings
from judge.models import ContestParticipation, ContestTag, Problem, Profile, Rating, Submission
from judge.views.api.srlp.srlp_utils_api import *
from django.db.models import F, OuterRef, Prefetch, Subquery
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
import json 
from munch import DefaultMunch
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from judge.jinja2.gravatar import gravatar_username

@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def get_ranking(request):
    queryset = Profile.objects.filter(is_unlisted=False)
    queryset = queryset.annotate(username=F('user__username'), rank=F('display_rank'))

    queryset = filter_if_not_none(queryset,
        username__icontains = request.GET.get('username'),
        rank__icontains = request.GET.get('rank')
    )    
    queryset = order_by_if_not_none(queryset,
            request.GET.getlist('order_by')                  
    )
    
    queryset = queryset.values('username', 'points', 'performance_points', 'rank', 'problem_count', 'last_access')

    if len(queryset)> 0:
        paginator = CustomPagination()
        result_page = DefaultMunch.fromDict(paginator.paginate_queryset(queryset, request))
        data = ({"ranking": {res.username: 
                    {   'avatar_url': gravatar_username(res.username),
                        'points': res.points, #TODO: Ver diferencia entre points y performance_points 
                        'problem_count': res.problem_count,
                        'performance_points': res.performance_points,
                        'last_access': res.last_access,
                        'rank': res.rank,
                    } 
            for res in result_page}})
        return paginator.get_paginated_response(data)
    else:
        return Response({})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
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

    last_rating = profile.ratings.last()

    contest_history = {}
    participations = ContestParticipation.objects.filter(user=profile, virtual=0, contest__is_visible=True,
                                                         contest__is_private=False,
                                                         contest__is_organization_private=False)
    
    for contest_key, rating, mean, performance in participations.values_list(
        'contest__key', 'rating__rating', 'rating__mean', 'rating__performance',
    ):
        contest_history[contest_key] = {
            'rating': rating,
            'raw_rating': mean,
            'performance': performance,
        }

    resp['contests'] = {
        'current_rating': last_rating.rating if last_rating else None,
        'history': contest_history,
    }

    return Response(resp)
