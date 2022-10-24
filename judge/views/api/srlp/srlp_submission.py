
import jwt
from dmoj import settings
from judge.models import Problem, Judge, Profile, Submission, SubmissionSource, ContestSubmission


from rest_framework.decorators import api_view, permission_classes
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from django.db import transaction
import json 
from munch import DefaultMunch
from django.shortcuts import get_list_or_404, get_object_or_404
from judge.models.runtime import Language

from judge.views.api.srlp.srlp_utils_api import get_jwt_user, CustomPagination, isLogueado, order_by_if_not_none, filter_if_not_none
from django.db.models import F
from judge.utils.raw_sql import join_sql_subquery, use_straight_join


@permission_classes([isLogueado])
@api_view(['GET'])
def get_info_submit(request):
    problem = get_object_or_404(Problem,code=request.GET.get('problem'))
    judges = Judge.objects.filter(online=True, problems=problem.id).values('name', 'name')
    languages = problem.usable_languages.order_by('name', 'key').values('name', 'key')

    return Response({'judges': judges, 'languages': languages})

@permission_classes([isLogueado])
@api_view(['POST'])
def sumbit_solution(request):
    user = get_jwt_user(request)
    profile= Profile.objects.get(user=user)
    data = DefaultMunch.fromDict(json.loads(request.body))
    language = get_object_or_404(Language, key=data.language_key)
    judge = get_object_or_404(Judge, name=data.judge_name)
    # language_key 
    # problem_id
    # source

    problem = Problem.objects.get(code=data.problem_code)

    if not problem.is_accessible_by(get_jwt_user(request)): 
        return Response({'status': False, 'message': 'El problema no existe o no se tiene acceso.'})
    
    if (   not user.has_perm('judge.spam_submission') and
            Submission.objects.filter(user=profile, rejudged_date__isnull=True)
                              .exclude(status__in=['D', 'IE', 'CE', 'AB']).count() >= settings.DMOJ_SUBMISSION_LIMIT
        ):
        return Response({'message': 'Has subido demasiadas soluciones.', 'status': False}, status=429)
        

    if not problem.allowed_languages.filter(id=language.id).exists():
        return Response({'message': 'Lenguaje de programación no disponible.', 'status': False}, status=429)
    
    if not user.is_superuser and problem.banned_users.filter(id=profile.id).exists():
        return Response({'message': 'No puedes subir soluciones, has sido declarado como persona no grata para este problema.'}, status=429)
    
    # Must check for zero and not None. None means infinite submissions remaining.
    if remaining_submission_count(profile, problem) == 0:
        return Response({'message': 'Excediste el límite de subida de solución al problema.'}, status=429)

    

    with transaction.atomic():
        submission = Submission.objects.create(user=profile, problem=problem, language=language)

        contest_problem = profile.current_contest

        if contest_problem is not None:
            # Use the contest object from current_contest.contest because we already use it
            # in profile.update_contest().
            submission.contest_object = profile.current_contest.contest
            if profile.current_contest.live:
                submission.locked_after = submission.contest_object.locked_after
            submission.save()
            ContestSubmission(
                submission=submission,
                problem=contest_problem,
                participation=profile.current_contest,
            ).save()
        else:
            submission.save()

        source = SubmissionSource(submission=submission, source=data.source)
        source.save()

    # Save a query.
    submission.source = source
    submission.judge(force_judge=True, judge_id=judge.name)

    return Response({'message': 'Subida de solución correcta!','status': True, 'id_sumbit': submission.id})

def remaining_submission_count(profile, problem):
    max_subs = contest_problem(profile, problem) and contest_problem(profile, problem).max_submissions
    if max_subs is None:
        return None
    # When an IE submission is rejudged into a non-IE status, it will count towards the
    # submission limit. We max with 0 to ensure that `remaining_submission_count` returns
    # a non-negative integer, which is required for future checks in this view.
    return max(
        0,
        max_subs - get_contest_submission_count(
            problem, profile, profile.current_contest.virtual,
        ),
    )

def contest_problem(profile, problem):
    if profile.current_contest is None:
        return None
    return get_contest_problem(problem, profile)

def get_contest_problem(problem, profile):
    try:
        return problem.contests.get(contest_id=profile.current_contest.contest_id)
    except ObjectDoesNotExist:
        return None

def get_contest_submission_count(problem, profile, virtual):
    return profile.current_contest.submissions.exclude(submission__status__in=['IE']) \
                  .filter(problem__problem=problem, participation__virtual=virtual).count()

@permission_classes([isLogueado])
@api_view(['GET'])
def get_info_submission(request):
    user = get_jwt_user(request)

    problem = Problem.objects.filter(code=request.GET.get('problem')).first()
    if(not problem or not problem.is_accessible_by(get_jwt_user(request))): 
        return Response({'status': False, 'message': 'El problema no existe o no tienes acceso.'})
    
    
    submission = Submission.objects.filter(user_id=user.id, problem_id=problem.id)
    submission = order_by_if_not_none(submission,
        request.GET.getlist('order_by')                  
    )

    if len(submission)> 0:
        paginator = CustomPagination()
        result_page = DefaultMunch.fromDict(paginator.paginate_queryset(submission, request))

        data = {
            'submissions': ({
            'id': res.id,
            'date': res.date,
            'language': res.language.key,
            'time': res.time,
            'memory': res.memory,
            'points': res.points,
            'result': res.result,
            'source': res.source.source,
            'error':  res.error
        } for res in result_page)
        }       
        return paginator.get_paginated_response(data)
    else:
        return Response({})

@permission_classes([isLogueado])
@api_view(['GET'])
def get_problem_info_submissions(request):
    
    problem = Problem.objects.filter(code=request.GET.get('problem')).first()
    if(not problem or not problem.is_accessible_by(get_jwt_user(request))): 
        return Response({'status': False, 'message': 'El problema no existe o no tienes acceso.'})
    
    submission = Submission.objects.filter(problem_id=problem.id)
    submission.annotate(username=F('user__user__username'))

    submission = order_by_if_not_none(submission,
        request.GET.getlist('order_by')                 
    )    
    
    submission = filter_if_not_none(submission, 
        username__icontains = request.GET.get('username')
    )

    if len(submission)> 0:
        paginator = CustomPagination()
        result_page = DefaultMunch.fromDict(paginator.paginate_queryset(submission, request))

        data = {
            'submissions': ({
                'id': res.id,
                #'problem': res.problem.code, #TODO: PUEDE SERVIR PARA OBTENER LOS ÚLTIMOS SUBMISSIONS
                'user': res.user.user.username,
                'date': res.date.isoformat(),
                'language': res.language.key,
                'time': res.time,
                'memory': res.memory,
                'points': res.points,
                'result': res.result,
            } for res in result_page)
        }       
        return paginator.get_paginated_response(data)
    else:
        return Response({})

@permission_classes([isLogueado])
@api_view(['GET'])
def get_all_submissions(request):
    
    submission = Submission.objects.filter(problem_id__in=Problem.get_visible_problems_rest(get_jwt_user(request)))
    
    submission = submission.annotate(
            username=F('user__user__username'), 
            problem_code=F('problem__code'), 
            problem_name=F('problem__name'),
            language_key=F('language__key')
        )
    submission = filter_if_not_none(submission, 
        username__icontains = request.GET.get('username'),
        result = request.GET.get('result'),
        language_key = request.GET.get('language_key'),
        problem_code__icontains =  request.GET.get('problem_code')
    )
    submission = submission.values('id', 'problem_code', 'problem_name', 'username', 'language_key', 'date', 'time', 'memory', 'points', 'result')
    submission = order_by_if_not_none(submission,
        request.GET.getlist('order_by')                 
    )
    if len(submission)> 0:
        paginator = CustomPagination()
        result_page = DefaultMunch.fromDict(paginator.paginate_queryset(submission, request))

        data = {
            'submissions': ({
                'id': res.id,
                'problem_code': res.problem_code,
                'problem_name': res.problem_name,
                'username': res.username,
                'date': res.date.isoformat(),
                'language_key': res.language_key,
                'time': res.time,
                'memory': res.memory,
                'points': res.points,
                'result': res.result,
            } for res in result_page)
        }       
        return paginator.get_paginated_response(data)
    else:
        return Response({})

def filter_submissions_by_visible_problems(queryset, user):
    join_sql_subquery(
        queryset,
        subquery=str(Problem.get_visible_problems_rest(user).distinct().only('id').query),
        params=[],
        join_fields=[('problem_id', 'id')],
        alias='visible_problems',
    )