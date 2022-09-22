
from dmoj import settings
from judge.models import Contest, Contest, ContestParticipation, ContestTag, Rating
from judge.views.api.srlp.utils_srlp_api import *
from django.db.models import F, OuterRef, Prefetch, Subquery
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view
from rest_framework.response import Response
from operator import attrgetter
from django.contrib.auth.models import User
import json 
from munch import DefaultMunch
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

def sane_time_repr(delta):
    days = delta.days
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    return '%02d:%02d:%02d' % (days, hours, minutes)

@api_view(['GET'])
def get_contest_list(request):
    user = get_jwt_user(request)
    contest_code = request.GET.getlist('code')[0]
    queryset = Contest.get_visible_contests(user).prefetch_related(
        Prefetch('tags', queryset=ContestTag.objects.only('name'), to_attr='tag_list'))

    if settings.ENABLE_FTS and 'search' in request.GET:
            query = contest_code
            if query:
                queryset = queryset.search(query)

    return Response({c.key: {
        'name': c.name,
        'start_time': c.start_time.isoformat(),
        'end_time': c.end_time.isoformat(),
        'time_limit': c.time_limit and sane_time_repr(c.time_limit),
        'labels': list(map(attrgetter('name'), c.tag_list)),
    } for c in queryset})


@api_view(['GET'])
def get_contest_info(request):
    user = get_jwt_user(request)

    contest = get_object_or_404(Contest, key=contest)

    #TODO: CUANDO REQUIERA LOGIN QUITAR COMENTARIOS
    #if not contest.is_accessible_by(request.user):
    #    raise Http404()

    in_contest = contest.is_in_contest(user)
    can_see_rankings = contest.can_see_full_scoreboard(user)

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

    return Response({
        'time_limit': contest.time_limit and contest.time_limit.total_seconds(),
        'start_time': contest.start_time.isoformat(),
        'end_time': contest.end_time.isoformat(),
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
        'rankings': [
            {
                'user': participation.username,
                'points': participation.score,
                'cumtime': participation.cumtime,
                'tiebreaker': participation.tiebreaker,
                'old_rating': participation.old_rating,
                'new_rating': participation.new_rating,
                'is_disqualified': participation.is_disqualified,
                'solutions': contest.format.get_problem_breakdown(participation, problems),
            } for participation in participations],
    })