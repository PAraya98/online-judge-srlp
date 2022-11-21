
from dmoj import settings
from judge.models import Contest, Contest, ContestParticipation, ContestTag, Rating
from judge.views.api.srlp.srlp_utils_api import *
from django.db.models import OuterRef, Subquery, BooleanField, Case, Count, F, FloatField, IntegerField, Max, Min, Q, Sum, Value, When, Prefetch, Window
from django.db.models.functions import Rank
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
    if(user): profile = Profile.objects.get(user=user) 

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

    else: return Response({'status': False, 'message': 'Consulta erróna.'}) 
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
                'time_before_start': c.time_before_start,
                'time_before_end': c.time_before_end,
                'locked_after': c.locked_after.timestamp() if c.locked_after else None,
                'is_locked': c.locked_after > timezone.now() if c.locked_after else False,
                'labels': list(map(attrgetter('name'), c.tag_list))
            })
        data = ({"contests": array, 'current_time': datetime.now(), 'is_connected': bool(user), 'status': True})
        return paginator.get_paginated_response(data)
    else:   
        return Response({'status': True, 'pages': 0, 'contests': [], 'current_time': datetime.now(), 'is_connected': bool(user)})


@api_view(['GET'])
def get_contest_info(request):
    user = get_jwt_user(request)
    code = request.GET.getlist('code')
    contest_code = '' if not code else code[0]
    contest = Contest.objects.filter(key=contest_code).first()

    if not (contest and contest.is_accessible_by(user)):
       return Response({'status': False, 'message': 'El concurso no existe o no tienes acceso a este concurso.'})

    in_contest = contest.is_in_contest_rest(user)

    problems = list(contest.contest_problems.select_related('problem')
                    .defer('problem__description').order_by('order'))

    can_see_problems = (in_contest or contest.ended or contest.is_editable_by(user))

    user_context = {
        'is_connected': bool(user)
    }
    if user:    
        user_context['is_virtual_participation'] = bool(request.profile.current_contest) and request.profile.current_contest.contest.key == contest.key and request.profile.current_contest.virtual != 0
        user_context['is_in_contest'] = contest.is_in_contest_rest(user)
        user_context['can_see_full_scoreboard'] = contest.can_see_full_scoreboard_rest(user)   
        user_context['can_see_own_scoreboard'] = contest.can_see_own_scoreboard(user)
        user_context['has_completed_contest'] = contest.has_completed_contest_rest(user)
        user_context['live_joinable'] = contest.is_live_joinable_by(user)
        user_context['editable'] = contest.is_editable_by(user)
        user_context['has_participated'] = bool(ContestParticipation.objects.filter(user=Profile.objects.get(user=user), contest=contest).first())


    return Response({
        'name': contest.name,
        'description': contest.description,
        'summary': contest.summary,
        'time_limit': contest.time_limit and contest.time_limit.total_seconds(),
        'has_started': contest.started,
        'start_time': contest.start_time.isoformat(),
        'end_time': contest.end_time.isoformat(),
        'has_ended': contest.ended,
        'current_time': datetime.now(),
        'tags': list(contest.tags.values_list('name', flat=True)),
        'is_rated': contest.is_rated,
        'rate_all': contest.is_rated and contest.rate_all,
        'has_rating': contest.ratings.exists(),
        'rating_floor': contest.rating_floor,   
        'rating_ceiling': contest.rating_ceiling,
        'has_access_code': True if contest.access_code is not '' else False,
        'time_before_start': contest.time_before_start,
        'time_before_end': contest.time_before_end,
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
                'ac_rate': problem.problem.ac_rate
            } for problem in problems] if can_see_problems else [],
        'user_context': user_context,
        'status': True
    })

@api_view(['GET'])
def get_contest_ranking(request):
    code = request.GET.getlist('code')
    contest_code = '' if not code else code[0]
    contest = Contest.objects.filter(key=contest_code).first()

    if not (contest and contest.is_accessible_by(request.user)):
       return Response({'status': False, 'message': 'El concurso no existe o no tienes acceso a este concurso.'})

    problems = list(contest.contest_problems.select_related('problem')
                .defer('problem__description').order_by('order'))
    new_ratings_subquery = Rating.objects.filter(participation=OuterRef('pk'))
    old_ratings_subquery = (Rating.objects.filter(user=OuterRef('user__pk'),
                            contest__end_time__lt=OuterRef('contest__end_time'))
                        .order_by('-contest__end_time'))

    queryset = (contest.users
                    .annotate(new_rating=Subquery(new_ratings_subquery.values('rating')[:1]))
                    .annotate(old_rating=Subquery(old_ratings_subquery.values('rating')[:1]))
                    .prefetch_related('user__organizations')
                    .annotate(username=F('user__user__username'))
                    .order_by('-score', 'cumtime', 'tiebreaker'))
    
    
    if request.GET.get('virtual') == 'true':
        queryset = queryset.exclude(virtual = 0)
    else:
        queryset = filter_if_not_none(queryset,        
            virtual = 0 if request.GET.get('virtual') == 'false' else None
        )  

    #if(not contest.is_editable_by(user)):
    #    queryset = queryset.exclude(virtual__lt = 0)
    
    queryset = queryset.annotate(
        position=Window(
            expression=Rank(),
            order_by=F('score').desc(),
    ))
    
    if not contest.can_see_own_scoreboard(request.user):
        return Response({'status': False, 'own_ranking': False,'has_ended': contest.ended, 'message': 'No tienes acceso para ver el ranking.'})
    
    contest_problems = contest.problems.all()

    user_best = queryset.filter(user=request.profile).first()
    if user_best:  
        user_participation =    {   'position': user_best.position,
                                    'user': user_best.username,
                                    'virtual': user_best.virtual,
                                    'points': user_best.score,
                                    'cumtime': user_best.cumtime,
                                    'tiebreaker': user_best.tiebreaker,
                                    'old_rating': user_best.old_rating,
                                    'new_rating': user_best.new_rating,
                                    'is_disqualified': user_best.is_disqualified,                                    
                                    'solutions': get_participation_info(contest_problems, user_best, request.user)
                                }

    else: user_participation = None

    if not contest.can_see_full_scoreboard_rest(request.user): 
        return Response({'status': False, 'own_ranking': True, 'has_ended': contest.ended, 'user_participation': user_participation, 'message': 'No tienes acceso para ver el ranking general.'})

    if(len(queryset) > 0):
        paginator = CustomPagination()
        result_page = paginator.paginate_queryset(queryset, request)

        ranking = [
            {   'position': participation.position,
                'user': participation.username,
                'virtual': participation.virtual,
                'points': participation.score,
                'cumtime': participation.cumtime,
                'tiebreaker': participation.tiebreaker,
                'old_rating': participation.old_rating,
                'new_rating': participation.new_rating,
                'is_disqualified': participation.is_disqualified,
                #'solutions': contest.format.get_problem_breakdown(participation, problems),
                'solutions': get_participation_info(contest_problems, participation, request.user)
            } for participation in result_page]
        data = {'ranking': ranking, 'has_ended': contest.ended,'own_ranking': True, 'user_participation': user_participation, 'status': True}
        return paginator.get_paginated_response(data)
    else:
        return Response({'ranking': [], 'own_ranking': True, 'has_ended': contest.ended,'user_participation': user_participation, 'pages': 0, 'status': True})

def get_participation_info(contest_problems, participation, user):
    data = []
    for problem in contest_problems:
        submission_data = participation.submissions.filter(problem__problem=problem).order_by('-submission__points', 'submission__time').first()
        
        if submission_data:
            test_cases = submission_data.submission.test_cases
            total_testcases = test_cases.count()
            correct_testcases = test_cases.filter(status='AC').count()
            data.append({   'problem_name':         problem.name,
                            'has_submission':       True,
                            'id':                   submission_data.submission.id,
                            'can_see_detail':       submission_data.submission.can_see_detail(user),
                            'language_name':        submission_data.submission.language.name,
                            'result_code':          submission_data.submission.result, 
                            'date':                 submission_data.submission.date,
                            'time':                 submission_data.submission.time,
                            'points':               submission_data.submission.points,   
                            'total_points':         problem.points,
                            'total_testcases':      total_testcases,
                            'correct_testcases':    correct_testcases
                            #CANTIDAD DE INTENTOS (?) TODO: quizás
                        })
        else:
            data.append({   'problem_name':     problem.name,
                            'has_submission':   False              
                        })
    return data


@permission_classes([isLogueado]) 
@api_view(['POST'])
def join_contest(request):
    data = DefaultMunch.fromDict(json.loads(request.body))
    contest_code = data.contest_code
    access_code = data.access_code
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
               return Response({'status': False, 'message': 'Se ha acabado tu tiempo de participación, espera a que termine el concurso.'})

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
def get_time__(request):
    contest_key = request.GET.get('contest_key')
    if not contest_key: return Response({'status': False, 'message': 'Consulta errónea.'})
    contest = Contest.objects.filter(key=contest_key).first()    
    
    if(contest and contest.is_accessible_by(request.user)):
        timezone_now = timezone.now().timestamp()        
        if contest.started and (not contest.ended or (contest.time_limit and request.profile and request.profile.current_contest and request.profile.current_contest.contest.key == contest.key) ):
            conditional_time = None
            message = ''
            ### Time condition

            has_locked_time = contest.locked_after and contest.locked_after < contest.end_time

            if has_locked_time:
                has_limit_time = contest.time_limit and request.profile and request.profile.current_contest and request.profile.current_contest.contest.key == contest.key \
                    and ((contest.time_limit + request.profile.current_contest.real_start) < contest.locked_after or contest.ended)
                                 
                if has_limit_time:
                    conditional_time = (contest.time_limit + request.profile.current_contest.real_start).timestamp()
                    message = 'Tú tiempo limite termina en: '  
                else:
                    
                    conditional_time = contest.locked_after.timestamp() + 0.5
                    message = 'El concurso se bloquea en: '  
            else:
                has_limit_time = contest.time_limit and request.profile and request.profile.current_contest and request.profile.current_contest.contest.key == contest.key \
                    and ((contest.time_limit + request.profile.current_contest.real_start) < contest.end_time or contest.ended)

                if has_limit_time: 
                    conditional_time = (contest.time_limit + request.profile.current_contest.real_start).timestamp()
                    message = 'Tú tiempo limite termina en: '  
                else:
                    conditional_time = contest.end_time.timestamp() + 0.5  
                    message = 'El concurso termina en: '         
            
            return Response({   'status': True, 
                                'server_time': timezone_now, 
                                'time': conditional_time, 
                                'message': message})
        elif contest.ended:
            return Response({   'status': True, 
                                'server_time': timezone_now, 
                                'time': timezone_now, 
                                'message': 'Concurso terminado.'
                            })
        else:
            return Response({   'status': True, 
                                'server_time': timezone_now, 
                                'time': contest.start_time.timestamp() + 0.5, 
                                'message': 'Empieza en :'
                            })
    else:
        return Response({   'status': False, 
                            'message': 'El concurso no existe o no tienes acceso.'
                        })

@permission_classes([isLogueado]) 
@api_view(['GET'])
def get_time(request):
    contest = Contest.objects.filter(key=request.GET.get('contest_key')).first()

    if not (contest and contest.is_accessible_by(request.user)): 
        return Response({'status': False, 'message': 'El concurso no existe o no tienes acceso.'})
    
    profile = request.profile

    #Conditions for time_limit time
    if profile and contest.time_limit and profile.current_contest and profile.current_contest.contest.key == contest.key and not (profile.id in contest.spectator_ids):
        if  profile.current_contest.virtual != 0 or (profile.current_contest.virtual == 0 \
            and ((contest.locked_after and contest.time_limit + profile.current_contest.real_start < contest.locked_after) \
            or contest.time_limit + profile.current_contest.real_start < contest.end_time)):
             return Response({
                'status': True, 
                'server_time': timezone.now().timestamp(), 
                'time': (contest.time_limit + request.profile.current_contest.real_start).timestamp(),
                'message': 'Tú tiempo límite termina en:'
            })
    if contest.started and not contest.ended:
        if contest.locked_after and contest.locked_after < contest.end_time and timezone.now() < contest.locked_after:
            return Response({
                'status': True, 
                'server_time': timezone.now().timestamp(), 
                'time': contest.locked_after.timestamp() + 0.5,
                'message': 'El concurso se bloqueara en:'
            })
        else:
            return Response({
                'status': True, 
                'server_time': timezone.now().timestamp(), 
                'time': contest.end_time.timestamp() + 0.5,
                'message': 'El concurso termina en:'
            })
    elif contest.ended:
        return Response({
            'status': True, 
            'server_time': timezone.now().timestamp(), 
            'time': timezone.now().timestamp(),
            'message': 'El concurso ha terminado:'
        })
    else: # contest is in coming:
        return Response({   
            'status': True, 
            'server_time': timezone.now().timestamp(), 
            'time': contest.start_time.timestamp() + 0.5, 
            'message': 'El concurso empieza en:'
            })
