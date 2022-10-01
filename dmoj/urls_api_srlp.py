from django.urls import include, path, re_path, reverse
from judge.views.api.srlp import srlp_admin, srlp_auth, srlp_contest, srlp_user, srlp_problem

auth_patterns = [
    path('register', srlp_auth.register),
    path('login', srlp_auth.get_tokens_for_user),
    path('validation', srlp_auth.validation),
]

user_patterns = [
    path('get_ranking', srlp_user.get_ranking),
    path('info', srlp_user.get_user_info)
]

problem_patterns = [
    path('list', srlp_problem.get_problem_list),
    path('info', srlp_problem.get_problem_info)
]

contest_patterns = [
    path('list', srlp_contest.get_contest_list),
    path('info', srlp_contest.get_contest_info)
]

admin_patterns = [
    path('list_users', srlp_admin.get_users_info),
    path('user_data', srlp_admin.get_user_data),
]

srlp_patterns= [
    path('auth/', include(auth_patterns)),
    path('user/', include(user_patterns)),
    path('problem/', include(problem_patterns)),
    path('contest/', include(contest_patterns)),
    path('admin/', include(admin_patterns))
]
