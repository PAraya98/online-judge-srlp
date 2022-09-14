from operator import attrgetter
import base64
import hmac
from django.utils.encoding import force_bytes
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db.models import Count, F, OuterRef, Prefetch, Q, Subquery
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import BaseListView
from django.contrib.auth.models import User

from judge.models import (
    Contest, ContestParticipation, ContestTag, Judge, Language, Organization, Problem, ProblemType, Profile, Rating,
    Submission,
)
from judge.utils.infinite_paginator import InfinitePaginationMixin
from judge.utils.raw_sql import join_sql_subquery, use_straight_join
from judge.views.submission import group_test_cases


class APIUserMagnament():

    def register(request):
        
        user, _ = User.objects.create(username='paraya104', email='pedro104@alumnos.uta.cl')
        User.set_password(user, 'adasd')
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'language': Language.get_default_language(),
            }
        ) 
        profile.timezone = 'America/Toronto'
        profile.organizations.add(Organization.objects.get(id=1))
        profile.save()
        hmac.new(force_bytes(settings.SECRET_KEY), msg=secret, digestmod='sha256').hexdigest()
        
        return JsonResponse(
            {   'State': created,
            }, 
            status=422
        )