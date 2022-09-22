from rest_framework_simplejwt.authentication import JWTAuthentication

def get_jwt_user(request):
    user = JWTAuthentication().authenticate(request)
    return None if user is None else user[0]