
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
def get_problem_list(request):
    queryset = Problem.get_public_problems()
    if settings.ENABLE_FTS and 'search' in request.GET:
        query = ' '.join(request.GET.getlist('search')).strip()
        if query:
            queryset = queryset.search(query)
    queryset = queryset.values_list('code', 'points', 'partial', 'name', 'group__full_name')

    return Response({code: {
        'points': points,
        'partial': partial,
        'name': name,
        'group': group,
    } for code, points, partial, name, group in queryset})



#@action(methods=['GET'], detail=False)
#def api_schema(self, request):
#    meta = self.metadata_class()
#    data = meta.determine_metadata(request, self)
#    return Response(data)