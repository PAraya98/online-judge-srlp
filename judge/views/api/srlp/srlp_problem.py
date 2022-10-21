
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
from django.db.models import F, OuterRef, Subquery
from judge.models.problem import ProblemType

from judge.views.api.srlp.srlp_utils_api import get_jwt_user, CustomPagination, filter_conjuntive_if_not_none, order_by_if_not_none, filter_if_not_none

from judge.jinja2.markdown import markdown

@api_view(['GET'])
def get_problem_list(request):
    queryset = Problem.get_public_problems() #TODO: Cambiar para organizaciones "Curso"

    queryset = queryset.annotate(group_name=F('group__full_name'))
    
    queryset = filter_if_not_none(
        queryset,
        name__icontains=request.GET.get('name'),
        code__icontains=request.GET.get('code'),
        group_name__icontains=request.GET.get('group_name'),
        is_public = request.GET.get('is_public'),
        is_organization_private = request.GET.get('is_organization_private'),
        types__name__in = request.GET.getlist('type_name') 
    )

    queryset = order_by_if_not_none(queryset,
            request.GET.getlist('order_by')                  
    )

    #queryset = queryset.values('id', 'code', 'points', 'partial', 'name', 'group_name', 'user_count', 'ac_rate', 'is_public', 'is_organization_private', 'group_id', 'date', 'types')
    


    if len(queryset)> 0:
        paginator = CustomPagination()
        result_page = DefaultMunch.fromDict(paginator.paginate_queryset(queryset, request))

        #TODO: PARA HACER JOIN SIN CLAVE FORANEA
        #values = ProblemType.objects.filter(id__in=Problem.objects.filter(id=res.id).values('types')).values('name')
        #array = []
        #for types in values:
        #    array.append(types['name'])
        #res.types = array

        #for res in result_page:     
        #    p = Problem.objects.get(id=res.id)
        #    res.types = list(p.types.values_list('full_name', flat=True))

        data = {
            'problems': ({
                'code':  res.code,
                'points': res.points,
                'partial': res.partial,
                'name': res.name,
                'group_name': res.group_name,
                'date': res.date,
                'user_count': res.user_count,
                'is_public': res.is_public,
                'is_organization_private': res.is_organization_private,
                'group_id': res.group_id,
                'types': list(res.types.values())
            } for res in result_page)
        }       
        return paginator.get_paginated_response(data)
    else:
        return Response({})

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
        'description2': markdown(p.description, p.markdown_style)
    })
    
#@action(methods=['GET'], detail=False)
#def api_schema(self, request):
#    meta = self.metadata_class()
#    data = meta.determine_metadata(request, self)
#    return Response(data)

@api_view(['GET'])
def get_types(request):
    queryset = ProblemType.objects; #TODO: Cambiar para organizaciones "Curso"

    queryset = filter_if_not_none(
        queryset,
        name__icontains=request.GET.get('name'),
        full_name__icontains=request.GET.get('full_name')
    )

    queryset = order_by_if_not_none(queryset,
            request.GET.getlist('order_by')                  
    )
    
    queryset = queryset.values('id', 'name', 'full_name')

    if len(queryset)> 0:
        paginator = CustomPagination()
        result_page = DefaultMunch.fromDict(paginator.paginate_queryset(queryset, request))

        data = {
            'types': ({
                'id':   res.id,
                'name':  res.name,
                'full_name': res.full_name
                #TODO: AGREGAR ENLACE DE LA WIKI A FUTURO
            } for res in result_page)
        }       
        return paginator.get_paginated_response(data)
    else:
        return Response({})