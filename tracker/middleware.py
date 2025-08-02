# Create a new file middleware.py
from django.contrib.sessions.middleware import SessionMiddleware

class PersistentSessionMiddleware(SessionMiddleware):
    def process_request(self, request):
        super().process_request(request)
        # Force session to be saved if it hasn't been already
        if not request.session.session_key:
            request.session.save()