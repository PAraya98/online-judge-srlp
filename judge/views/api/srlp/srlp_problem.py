
from dmoj import settings
from judge.models import ContestParticipation, ContestTag, Problem, Profile, Rating, Submission, Language, JupyterWiki


from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
import json 
from munch import DefaultMunch
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import F, OuterRef, Subquery
from judge.models.problem import ProblemType

from judge.views.api.srlp.srlp_utils_api import get_jwt_user, CustomPagination, filter_conjuntive_if_not_none, order_by_if_not_none, filter_if_not_none, isProfesor

from judge.jinja2.markdown import markdown

@api_view(['GET'])
def get_problem_list(request):
    queryset = Problem.get_visible_problems_rest(get_jwt_user(request)).distinct() 

    queryset = queryset.annotate(group_name=F('group__full_name'))
    
    queryset = filter_if_not_none(
        queryset,
        name__icontains=request.GET.get('name'),
        code__icontains=request.GET.get('code'),
        group_name__icontains=request.GET.get('group_name'),
        is_public = request.GET.get('is_public'),
        is_organization_private = request.GET.get('is_organization_private')
    )

    queryset = filter_conjuntive_if_not_none(queryset, 'types__id__in',
        request.GET.getlist('type_id')
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
    p = Problem.objects.filter(code=problem_code).first()
    if not p and not p.is_accessible_by(get_jwt_user(request)): 
        return Response({'status': False, 'message': 'El problema no existe o no se tiene acceso.'})

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
        name__icontains = request.GET.get('name'),
        full_name__icontains = request.GET.get('full_name'),
        wikis__in= filter_if_not_none(JupyterWiki.objects,
                title__icontains = request.GET.get('wiki_title'),
                author__user__username__icontains = request.GET.get('wiki_author'),
                language__key = request.GET.get('wiki_language_key').distinct()
            ) 
    )

    queryset = order_by_if_not_none(queryset,
            request.GET.getlist('order_by')                  
    )
    
    #queryset = queryset.values('id', 'name', 'full_name')

    if len(queryset)> 0:
        paginator = CustomPagination()
        result_page = DefaultMunch.fromDict(paginator.paginate_queryset(queryset, request))

        data = [{
                'id':   res.id,
                'name':  res.name,
                'full_name': res.full_name,
                'wikis':    [   {   'id':       wiki.id,
                                    'author':   wiki.author.user.username, 
                                    'title':    wiki.title, 
                                    'language': wiki.language.name
                                } for wiki in res.wikis.all()
                            ]
                #TODO: AGREGAR ENLACE DE LA WIKI A FUTURO
            } for res in result_page]
              
        return paginator.get_paginated_response({'types': data, 'status': True})
    else:
        return Response({'types': [], 'status': True, 'pages': 0})


@api_view(['POST'])
@permission_classes([isProfesor])
def create_wiki(request):
    data = DefaultMunch.fromDict(json.loads(request.body))
    problem_type_name = data.problem_type_name
    wiki_title = data.wiki_title
    wiki_content = data.wiki_content
    language_key = data.wiki_language_key
    user = get_jwt_user(request)
    profile= Profile.objects.get(user=user)

    language = Language.objects.filter(key = language_key).first()
    problem_type = ProblemType.objects.filter(name = problem_type_name).first()

    if(language and problem_type and wiki_title and wiki_content):
        
        if(JupyterWiki.objects.filter(title=wiki_title, language=language).first()): 
            return Response({'status': False, 'message': 'Esta wiki ya existe, intenta con otro título.'})
        
        wiki = JupyterWiki.objects.create(author= profile,title=wiki_title, content=wiki_content, language=language)
        wiki.save()
        problem_type.wikis.add(wiki)
        return Response({'status': True, 'message': 'Wiki añadida correctamente.', 'wiki_id': wiki.id})
    else:
        return Response({'status': False, 'message': 'Solicitud de creación de Wiki incorrecta.'})

@api_view(['POST'])
@permission_classes([isProfesor])
def modify_wiki(request):
    data = DefaultMunch.fromDict(json.loads(request.body))
    problem_type_name = data.problem_type_name
    wiki_id = data.wiki_id   
    user = get_jwt_user(request)
    profile= Profile.objects.get(user=user)
    problem_type = ProblemType.objects.filter(name = problem_type_name).first()

    if(problem_type):
        if(user.is_superuser):
            wiki = JupyterWiki.objects.filter(id=wiki_id).first()
        else:
            wiki = JupyterWiki.objects.filter(id=wiki_id, author=profile).first()
        if(not wiki):
            return Response({'status': False, 'message': 'Esta wiki no existe o no puedes modificarla.'})

        wiki.title = data.new_wiki_title if data.new_wiki_title else wiki.title
        wiki.content = data.new_wiki_content if data.new_wiki_content else wiki.content
        language = Language.objects.filter(key = data.new_wiki_language_key).first()
        wiki.language = wiki.language if not language else language
        wiki.save()

        return Response({'status': True, 'message': 'Wiki modificada correctamente.'})
    else:   
        return Response({'status': False, 'message': 'Solicitud de modificación de Wiki incorrecta.'})

@api_view(['POST'])
@permission_classes([isProfesor])
def delete_wiki(request):
    data = DefaultMunch.fromDict(json.loads(request.body))
    wiki_id = data.wiki_id   
    user = get_jwt_user(request)
    profile= Profile.objects.get(user=user)

    if(user.is_superuser):
        wiki = JupyterWiki.objects.filter(id=wiki_id).first()
    else:
        wiki = JupyterWiki.objects.filter(id=wiki_id, author=profile).first()

    if(not wiki):
        return Response({'status': False, 'message': 'Esta wiki no existe o no puedes modificarla.'})
    wiki.delete()
    return Response({'status': True, 'message': 'Wiki eliminada correctamente.'})

@api_view(['GET'])
def get_wiki(request):
    data = DefaultMunch.fromDict(json.loads(request.body))
    wiki_id = data.wiki_id 
    wiki = JupyterWiki.objects.filter(id=wiki_id).first()
    if(not wiki):
        return Response({'status': False, 'message': 'Esta wiki no existe.'})
    
    return Response({
        'status': True, 
        'wiki': {
            'title': wiki.title,
            'author': wiki.author.user.username,
            'content': wiki.content,
            'language': wiki.language.name,
            'type': wiki.problemtype.first().name
        }
    })

@api_view(['GET'])
def list_wiki(request):
    data = DefaultMunch.fromDict(json.loads(request.body))
    wiki_id = data.wiki_id 
    wiki = JupyterWiki.objects.filter(id=wiki_id).first()
    if(not wiki):
        return Response({'status': False, 'message': 'Esta wiki no existe.'})
    
    return Response({
        'status': True, 
        'wiki': {
            'title': wiki.title,
            'author': wiki.author.user.username,
            'content': wiki.content,
            'language': wiki.language.name,
            'type': wiki.problemtype.first().name
        }
    })

