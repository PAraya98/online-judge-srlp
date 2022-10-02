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
from django.shortcuts import get_object_or_404

from judge.views.api.srlp.utils_srlp_api import get_jwt_user

@api_view(['GET'])
def get_problem_list(request):   
    queryset = Problem.get_visible_problems(get_jwt_user(request))
    print(request.GET.getlist('list'))
    if settings.ENABLE_FTS and 'list' in request.GET:
        query = ' '.join(request.GET.getlist('list')).strip()
        print(query)
        if query:
            queryset = queryset.search(query)
    queryset = queryset.values_list('code', 'points', 'partial', 'name', 'group__full_name')
    return Response({code: {
        'points': points,
        'partial': partial,
        'name': name,
        'group': group,
    } for code, points, partial, name, group in queryset})


@api_view(['GET'])
def get_problem_info(request):
    code = request.GET.getlist('code')
    problem_code = '' if not code else code[0]
    p = get_object_or_404(Problem, code=problem_code)
    
    #TODO: CUANDO REQUIERA LOGIN QUITAR COMENTARIOS
    #if not p.is_accessible_by(get_jwt_user(request), skip_contest_problem_check=True):
    #    raise Response(status=404)

    return Response({
        'name': p.name,
        'authors': list(p.authors.values_list('user__username', flat=True)),
        'types': list(p.types.values_list('full_name', flat=True)),
        'group': p.group.full_name,
        'time_limit': p.time_limit,
        'memory_limit': p.memory_limit,
        'points': p.points,
        'partial': p.partial,
        'languages': list(p.allowed_languages.values_list('key', flat=True)),
        'description': p.description,        
    })
#@action(methods=['GET'], detail=False)
#def api_schema(self, request):
#    meta = self.metadata_class()
#    data = meta.determine_metadata(request, self)
#    return Response(data)