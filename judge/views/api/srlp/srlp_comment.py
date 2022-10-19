
from dmoj import settings
from judge.models import Problem, Judge, Profile, Submission, SubmissionSource, ContestSubmission, Comment


from rest_framework.decorators import api_view, permission_classes
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from django.db import transaction
import json 
from munch import DefaultMunch
from django.shortcuts import get_list_or_404, get_object_or_404
from judge.models.runtime import Language

from judge.views.api.srlp.srlp_utils_api import get_jwt_user, CustomPagination, isLogueado, filter_if_not_none

@permission_classes([isLogueado])
@api_view(['POST'])
def create_comment(request):
    data = DefaultMunch.fromDict(json.loads(request.body))
    user = get_jwt_user(request)
    profile= Profile.objects.get(user=user)
    comment = Comment.objects.create(page=data.page, author=profile, body=data.body, parent=data.parent)
    if(comment.is_accessible_by(user)):
        comment.save()
        return Response({'status': True})
    else:
        return Response({'status': False})

@api_view(['GET'])
def get_comments(request):
    comment_aux = Comment.objects.create(page=request.GET.getlist('page_code')[0], author_id=1)
    if(comment_aux.is_public() or comment_aux.is_accessible_by(get_jwt_user(request))):
        queryset = Comment.objects.filter(page=request.GET.getlist('page_code')[0]).exclude(hidden=True).values()
        if len(queryset)> 0:
            paginator = CustomPagination()
            result_page = DefaultMunch.fromDict(paginator.paginate_queryset(queryset, request))

            data = {
                'Comments': result_page
            }       
            return paginator.get_paginated_response(data)
        else:
            return Response({})
    else:
        return Response({'status': False})
