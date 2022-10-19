
from dmoj import settings
from judge.models import Problem, Judge, Profile, Submission, SubmissionSource, ContestSubmission, Comment, profile


from rest_framework.decorators import api_view, permission_classes
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from django.db import transaction
import json 
from munch import DefaultMunch
from django.shortcuts import get_list_or_404, get_object_or_404
from judge.models.runtime import Language
from django.contrib.auth.models import User
from judge.views.api.srlp.srlp_utils_api import get_jwt_user, CustomPagination, isLogueado, filter_if_not_none
from judge.jinja2.gravatar import gravatar_username

@permission_classes([isLogueado])
@api_view(['POST'])
def create_comment(request):
    data = DefaultMunch.fromDict(json.loads(request.body))
    comment_aux = get_list_or_404(Comment, page=data.page_code)[0]    
    if(comment_aux.is_accessible_by(get_jwt_user(request))):

        user = get_jwt_user(request)
        profile= Profile.objects.get(user=user)

        if not user.is_staff and not profile.has_any_solves:
            return Response({'status': False, 'message': 'Debes resolver al menos un problema para poder comentar.'})
        
        if profile.mute:
            return Response({'status': False, 'message': 'Tú cuenta ha sido silenciada por el administrador.'})

        comment = Comment.objects.create(page=data.page_code, author_id=profile.id, body=data.body, parent=data.parent)
        
        if(comment.is_accessible_by(user)):
            comment.save()
            return Response({'status': True})
        else:
            return Response({'status': False, 'message': 'No tienes acceso a esta acción.'})

@api_view(['GET'])
def get_comments(request):
    comment_aux = get_list_or_404(Comment, page=request.GET.getlist('page_code')[0])[0]
    if(comment_aux.is_public() or comment_aux.is_accessible_by(get_jwt_user(request))):
        queryset = Comment.objects.filter(page=request.GET.getlist('page_code')[0]).exclude(hidden=True).values()
        if len(queryset)> 0:
            paginator = CustomPagination()
            result_page = DefaultMunch.fromDict(paginator.paginate_queryset(queryset, request))
            array = []
            for comment in result_page:
                profile = Profile.objects.get(id=comment.author_id)
                user = User.objects.get(id=profile.user_id)
                
                array.append({                    
                    "id": comment.id,
                    "parent_id": comment.parent_id,
                    "level": comment.level,
                    "lft": comment.lft,
                    "rght": comment.rght,
                    "tree_id": comment.tree_id,
                    "author": {
                        "username": user.username,
                        "gravatar": gravatar_username(user.username),
                        "rank": profile.display_rank
                    },
                    "time": comment.time,
                    "score": comment.score,
                    "body": comment.body,                    
                })
            data = {
                'Comments': array
            }       
            return paginator.get_paginated_response(data)
        else:
            return Response({})
    else:
        return Response({'status': False})
