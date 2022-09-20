from django.urls import include, path, re_path, reverse
from judge.views.api.srlp import srlp_auth, srlp_user, srlp_problem

auth_patterns = [
    path('register', srlp_auth.register),
    path('login', srlp_auth.get_tokens_for_user),
    path('validation', srlp_auth.validation),
]

user_patterns = [
    path('get_ranking', srlp_user.get_ranking)
]

problem_patterns = [
    path('list/<str:search>', srlp_problem.get_problem_list)
]

srlp_patterns= [
    path('auth/', include(auth_patterns)),
    path('user/', include(user_patterns)),
    path('problem/', include(problem_patterns))
]
