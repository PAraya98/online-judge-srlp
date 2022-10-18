
from dmoj import settings
from judge.models import ContestParticipation, ContestTag, Problem, Judge, Profile, Rating, Submission, SubmissionSource, ContestSubmission, RuntimeVersion

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from rest_framework.response import Response
from django.db import transaction
from django.contrib.auth.models import User
import json 
from munch import DefaultMunch
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_list_or_404, get_object_or_404
from django.db.models import F, OuterRef, Subquery, Prefetch
from judge.models.problem import ProblemType
from judge.models.runtime import Language

from judge.views.api.srlp.utils_srlp_api import get_jwt_user, CustomPagination, isLogueado, filter_if_not_none



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
    langague = get_object_or_404(Language, key=data.language_key)
    # language_key 
    # problem_id
    # source

    problem = Problem.objects.get(code=data.problem_code)

    
    if (   not user.has_perm('judge.spam_submission') and
            Submission.objects.filter(user=profile, rejudged_date__isnull=True)
                              .exclude(status__in=['D', 'IE', 'CE', 'AB']).count() >= settings.DMOJ_SUBMISSION_LIMIT
        ):
        return Response({'Message': 'You submitted too many submissions.', 'status': False}, status=429)
        

    if not problem.allowed_languages.filter(id=langague.id).exists():
        return Response({'Message': 'Languague unavaible.', 'status': False}, status=429)
    
    if not user.is_superuser and problem.banned_users.filter(id=profile.id).exists():
        return Response({'Message': 'Banned from submitting: You have been declared persona non grata for this problem. You are permanently barred from submitting this problem.'}, status=429)
    
    # Must check for zero and not None. None means infinite submissions remaining.
    if remaining_submission_count(profile, problem) == 0:
        return Response({'Message': 'Too many submissions. You have exceeded the submission limit for this problem.'}, status=429)

    

    with transaction.atomic():
        submission = Submission.objects.create(user=profile, problem=problem)
        submission.languague = langague.id

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
    submission.judge(force_judge=True, judge_id=data.judge_id)

    return Response({'Message': 'Sumbit ok!','status': True, 'id_sumbit': submission.id})

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
    problem = get_object_or_404(Problem,code=request.GET.get('problem'))
    submission = get_list_or_404(Submission, user_id=user.id, problem_id=problem.id)

    array = []
    for res in submission:
        array.append({
            'id': res.id,
            'problem': res.problem.code,
            'user': res.user.user.username,
            'date': res.date.isoformat(),
            'language': res.language.key,
            'time': res.time,
            'memory': res.memory,
            'points': res.points,
            'result': res.result,
        })

    return Response({
        'Submissions': array
    })


