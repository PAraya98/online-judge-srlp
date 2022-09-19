from django.urls import include, path, re_path, reverse

from judge.views.api import srlp_auth

srlp_auth_patterns = [
    [   path('register', srlp_auth.register),
        path('login', srlp_auth.get_tokens_for_user),
        path('validation', srlp_auth.HelloView.post),
    ]   
]

srlp_patterns= [
    path('/auth/', include(srlp_auth_patterns)),
]

