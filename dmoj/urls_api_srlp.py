from django.urls import include, path, re_path, reverse
from judge.views.api.srlp import srlp_auth, srlp_problems
auth_patterns = [
    path('register', srlp_auth.register),
    path('login', srlp_auth.get_tokens_for_user),
    path('validation', srlp_auth.HelloView.post),
       
]

srlp_patterns= [
    path('auth/', include(auth_patterns)),
]