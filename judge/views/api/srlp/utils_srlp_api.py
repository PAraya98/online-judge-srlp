from rest_framework_simplejwt.authentication import JWTAuthentication

def get_jwt_user(request):
    user = JWTAuthentication().authenticate(request)
    return user[0] if user is not None else None