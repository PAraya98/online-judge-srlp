from rest_framework.response import Response

class srlpMiddleware(object):
    
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        if request.user and request.user.is_authenticated \
           and request.userrequest.user.profile.current_contest != None \
           and request.user.profile.current_contest.contest.time_before_end == None:
            request.user.profile.current_contest = None
            request.user.profile.save()

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
    
    def process_exception(self, request, exception):
        return Response({'status': False, 'message': 'Error en el servidor. (500)'})