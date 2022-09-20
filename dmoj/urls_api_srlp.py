from django.urls import include, path, re_path, reverse
from judge.views.api.srlp import srlp_auth, srlp_user
auth_patterns = [
    path('register', srlp_auth.register),
    path('login', srlp_auth.get_tokens_for_user),
    path('validation', srlp_auth.HelloView.post),
       
]

user_patterns = [
    path('get_ranking', srlp_user.get_ranking)
]

srlp_patterns= [
    path('auth/', include(auth_patterns)),
    path('user/', include(user_patterns))
]
