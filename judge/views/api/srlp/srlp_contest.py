
from dmoj import settings
from judge.models import Contest, Contest, ContestParticipation, ContestTag, Rating
from judge.views.api.srlp.srlp_utils_api import *
from django.db.models import OuterRef, Subquery, BooleanField, Case, Count, F, FloatField, IntegerField, Max, Min, Q, Sum, Value, When, Prefetch
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from operator import attrgetter
from django.contrib.auth.models import User
import json 
from django.db import IntegrityError
from munch import DefaultMunch
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta, tzinfo
from functools import partial
from judge.utils.ranker import ranker
from itertools import chain
from django.utils import timezone

def sane_time_repr(delta):
    days = delta.days
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    return '%02d:%02d:%02d' % (days, hours, minutes)

@api_view(['GET'])
def get_contest_list(request):
    user = get_jwt_user(request)
    profile = Profile.objects.get(user=user) 

    queryset = Contest.get_visible_contests(user).prefetch_related(
        Prefetch('tags', queryset=ContestTag.objects.only('name'), to_attr='tag_list'))

    queryset = order_by_if_not_none(queryset,
            request.GET.getlist('order_by')                  
    )

    
    if(request.GET.get('type') == 'started'):
        queryset = queryset.filter(start_time__lte = timezone.now(), end_time__gt = timezone.now())

    elif(request.GET.get('type') == 'ended'):
        queryset = queryset.filter(end_time__lt = timezone.now())
   
    elif(request.GET.get('type') == 'coming_soon'):
        queryset = queryset.filter(start_time__gt = timezone.now())

    elif(user and request.GET.get('type') == 'participating'):
        if(profile.current_contest): 
            queryset = queryset.filter(id= profile.current_contest.contest.id)
        else: return Response({'status': False, 'message': 'El usuario no está participando en ningún concurso.'})

    else: return Response({'status': False, 'message': 'Consulta erronéa.'}) 
    #is_in_contest_rest TODO: sirve
    
    queryset = filter_if_not_none(queryset,        
        name__icontains = request.GET.get('name')
    )   

    if len(queryset)> 0:
        paginator = CustomPagination()
        result_page = paginator.paginate_queryset(queryset, request)
        #current_contest = profile.current_contest.contest.key if profile.current_contest is not None else None
        array = [] 
        for c in result_page:
            array.append({
                'key': c.key,
                'name': c.name,                
                'summary': c.summary,
                'start_time': c.start_time.isoformat(),
                'end_time': c.end_time.isoformat(),
                'time_limit': c.time_limit and sane_time_repr(c.time_limit),
                'labels': list(map(attrgetter('name'), c.tag_list))
            })
        data = ({"contests": array})
        return paginator.get_paginated_response(data)
    else:   
        return Response({'status': True, 'pages': 0, 'contests': []})


@api_view(['GET'])
def get_contest_info(request):
    user = get_jwt_user(request)
    code = request.GET.getlist('code')
    contest_code = '' if not code else code[0]
    contest = Contest.objects.filter(key=contest_code).first()

    if contest and (not user or not contest.is_accessible_by(user)):
       return Response({'status': False, 'message': 'El concurso no existe o no tienes acceso a este concurso.'})

    in_contest = contest.is_in_contest_rest(user)

    problems = list(contest.contest_problems.select_related('problem')
                    .defer('problem__description').order_by('order'))

    new_ratings_subquery = Rating.objects.filter(participation=OuterRef('pk'))
    old_ratings_subquery = (Rating.objects.filter(user=OuterRef('user__pk'),
                                                  contest__end_time__lt=OuterRef('contest__end_time'))
                            .order_by('-contest__end_time'))
    participations = (contest.users.filter(virtual=0)
                      .annotate(new_rating=Subquery(new_ratings_subquery.values('rating')[:1]))
                      .annotate(old_rating=Subquery(old_ratings_subquery.values('rating')[:1]))
                      .prefetch_related('user__organizations')
                      .annotate(username=F('user__user__username'))
                      .order_by('-score', 'cumtime', 'tiebreaker') if can_see_rankings else [])
    can_see_problems = (in_contest or contest.ended or contest.is_editable_by(user))


    user_context = {}
    user_context['is_in_contest'] = contest.is_in_contest_rest(user)
    user_context['can_see_full_scoreboard'] = contest.can_see_full_scoreboard_rest(user)   
    user_context['can_see_own_scoreboard'] = contest.can_see_own_scoreboard(user)
    user_context['has_completed_contest'] = contest.has_completed_contest_rest(user)
    user_context['live_joinable'] = contest.is_live_joinable_by(user)
    user_context['editable'] = contest.is_editable_by(user)


    return Response({
        'name': contest.name,
        'description': contest.description,
        'summary': contest.summary,
        'time_limit': contest.time_limit and contest.time_limit.total_seconds(),
        'start_time': contest.start_time.isoformat(),
        'end_time': contest.end_time.isoformat(),
        'current_time': datetime.now(),
        'tags': list(contest.tags.values_list('name', flat=True)),
        'is_rated': contest.is_rated,
        'rate_all': contest.is_rated and contest.rate_all,
        'has_rating': contest.ratings.exists(),
        'rating_floor': contest.rating_floor,
        'rating_ceiling': contest.rating_ceiling,
        'format': {
            'name': contest.format_name,
            'config': contest.format_config,
        },
        'problems': [
            {
                'points': int(problem.points),
                'partial': problem.partial,
                'name': problem.problem.name,
                'code': problem.problem.code,
            } for problem in problems] if can_see_problems else [],
        'user_context': user_context
        #'rankings': [
        #    {
        #        'user': participation.username,
        #        'points': participation.score,
        #        'cumtime': participation.cumtime,
        #        'tiebreaker': participation.tiebreaker,
        #        'old_rating': participation.old_rating,
        #        'new_rating': participation.new_rating,
        #        'is_disqualified': participation.is_disqualified,
        #        'solutions': contest.format.get_problem_breakdown(participation, problems),
        #    } for participation in participations],
    })


@permission_classes([isLogueado]) 
@api_view(['POST'])
def join_contest(request):
    data = DefaultMunch.fromDict(json.loads(request.body))
    contest_code = data.contest_code
    access_code = data.acces_code
    contest = Contest.objects.filter(key=contest_code).first()
    user = get_jwt_user(request)
    profile= Profile.objects.get(user=user)

    if not contest:
        return Response({'status': False, 'message': 'El concurso no existe'})

    if not contest.started and not (is_editor(user, profile, contest) or is_tester(user, profile, contest)):
        return Response({'status': False, 'message': 'El concurso no está en progreso.'}) 

    if not user.is_superuser and contest.banned_users.filter(id=profile.id).exists():
        return Response({'status': False, 'message': 'Has sido declarado persona no grata para este concurso, no tienes permitido permitirte.'})

    requires_access_code = (not can_edit(user, contest) and contest.access_code and access_code != contest.access_code)
    if contest.ended:
        if requires_access_code:
            return Response({'status': False, 'message': 'Acceso denegado.'})

        while True:
            virtual_id = max((ContestParticipation.objects.filter(contest=contest, user=profile)
                                .aggregate(virtual_id=Max('virtual'))['virtual_id'] or 0) + 1, 1)
            try:
                participation = ContestParticipation.objects.create(
                    contest=contest, user=profile, virtual=virtual_id,
                    real_start= datetime.now(),
                )
            # There is obviously a race condition here, so we keep trying until we win the race.
            except IntegrityError:
                pass
            else:
                break
    else:
        SPECTATE = ContestParticipation.SPECTATE
        LIVE = ContestParticipation.LIVE

        if contest.is_live_joinable_by(user):
            participation_type = LIVE
        elif contest.is_spectatable_by(user):
            participation_type = SPECTATE
        else:
            return Response({'status': False, 'message': 'No tienes permitido entrar a este concurso.'})
        try:
            participation = ContestParticipation.objects.get(
                contest=contest, user=profile, virtual=participation_type,
            )
        except ContestParticipation.DoesNotExist:
            if requires_access_code:
               return Response({'status': False, 'message': 'Acceso denegado.'})

            participation = ContestParticipation.objects.create(
                contest=contest, user=profile, virtual=participation_type,
                real_start=datetime.now(),
            )
        else:
            if participation.ended:
                participation = ContestParticipation.objects.get_or_create(
                    contest=contest, user=profile, virtual=SPECTATE,
                    defaults={'real_start': datetime.now()},
                )[0]

    profile.current_contest = participation
    profile.save()
    contest._updating_stats_only = True
    contest.update_user_count()
    
    return Response({'status': True, 'message': 'Has entrado al concurso '+contest.name+"."})

def is_editor(user, profile, contest):
        if not user.is_authenticated:
            return False 
        return profile.id in contest.editor_ids

def is_tester(user, profile, contest):
    if not user.is_authenticated:
        return False
    return profile.id in contest.object.tester_ids

def is_spectator(user, profile, contest):
    if not user.is_authenticated:
        return False
    return profile.id in contest.object.spectator_ids

def can_edit(user, contest):
    return contest.is_editable_by(user)

@permission_classes([isLogueado]) 
@api_view(['POST'])
def leave_contest(request):
    data = DefaultMunch.fromDict(json.loads(request.body))
    contest_code = data.contest_code
    user = get_jwt_user(request)
    profile= Profile.objects.get(user=user)
    contest = Contest.objects.filter(key=contest_code).first()
    
    if not contest: return Response({'status': False, 'message': 'El concurso no existe!'})

    if profile.current_contest is None or profile.current_contest.contest_id != contest.id:
        return Response({'status': False, 'message': 'No estás inscrito al concurso o no estás inscrito en algún concurso.'})

    profile.remove_contest()
    return Response({'status': True, 'message': 'Has salido del concurso '+contest.name+"."})

@permission_classes([isLogueado]) 
@api_view(['GET'])
def get_ranking(request):
    user = get_jwt_user(request)
    profile = Profile.objects.get(user=user) 
    code = request.GET.getlist('code')
    contest_code = '' if not code else code[0]
    contest = Contest.objects.filter(key=contest_code).first()
    if not contest: return Response({'status': False, 'message': 'El concurso no existe.'})
    
    if not contest.can_see_full_scoreboard(user):
            queryset = contest.users.filter(user=profile, virtual=ContestParticipation.LIVE)
            if(len(queryset) > 0):
                paginator = CustomPagination()
                result_page = paginator.paginate_queryset(queryset, request)
                print(result_page) #TODO: Revisar si son objetos, sino no sirve para pasar como queryset
                return get_contest_ranking_list(
                    user, profile, contest,
                    ranking_list= partial(base_contest_ranking_list, queryset=result_page),
                    ranker=lambda users, key: ((('???'), user) for user in users),
                )
    users, problems = get_contest_ranking_list(user, profile, contest)
    print(users, problems)
    return Response({'status': True, 'ranking': ''})
    

def contest_ranking_list(contest, problems):
    return base_contest_ranking_list(contest, problems, contest.users.filter(virtual=0)
                                     .prefetch_related('user__organizations')
                                     .order_by('is_disqualified', '-score', 'cumtime', 'tiebreaker'))

def get_contest_ranking_list(user, profile, contest, participation=None, ranking_list=contest_ranking_list,
                             show_current_virtual=True, ranker=ranker):
    problems = list(contest.contest_problems.select_related('problem').defer('problem__description').order_by('order'))

    users = ranker(ranking_list(contest, problems), key=attrgetter('points', 'cumtime', 'tiebreaker'))

    if show_current_virtual:
        if participation is None and user.is_authenticated:
            participation = profile.current_contest
            if participation is None or participation.contest_id != contest.id:
                participation = None
        if participation is not None and participation.virtual:
            users = chain([('-', make_contest_ranking_profile(contest, participation, problems))], users)      
    return users, problems

def base_contest_ranking_list(contest, problems, queryset):
    return [make_contest_ranking_profile(contest, participation, problems) for participation in
            queryset.select_related('user__user', 'rating').defer('user__about', 'user__organizations__about')]



ContestRankingProfile = namedtuple(
    'ContestRankingProfile',
    'id user css_class username points cumtime tiebreaker organization participation '
    'participation_rating problem_cells result_cell display_name',
)

def make_contest_ranking_profile(contest, participation, contest_problems):
    def display_user_problem(contest_problem):
        # When the contest format is changed, `format_data` might be invalid.
        # This will cause `display_user_problem` to error, so we display '???' instead.
        try:
            return contest.format.display_user_problem(participation, contest_problem)
        except (KeyError, TypeError, ValueError):
            return '???'

    user = participation.user
    return ContestRankingProfile(
        id=user.id,
        user=user.user,
        css_class=user.css_class,
        username=user.username,
        points=participation.score,
        cumtime=participation.cumtime,
        tiebreaker=participation.tiebreaker,
        organization=user.organization,
        participation_rating=participation.rating.rating if hasattr(participation, 'rating') else None,
        problem_cells=[display_user_problem(contest_problem) for contest_problem in contest_problems],
        result_cell=contest.format.display_participation_result(participation),
        participation=participation,
        display_name=user.display_name,
    )