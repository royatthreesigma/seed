"""
Uncomment the code below to enable Clerk authentication in your DRF backend.
Make sure to set the CLERK_SECRET_KEY
environment variable before using this code.
"""
# import os
# import logging
# from rest_framework.authentication import BaseAuthentication
# from rest_framework.exceptions import AuthenticationFailed
# from django.contrib.auth import get_user_model
# from clerk_backend_api import authenticate_request, AuthenticateRequestOptions, Clerk
# from django.utils import timezone

# logger = logging.getLogger(__name__)
# User = get_user_model()

# """
# We handle authntication using Clerk tokens.
# This is not a middleware but a DRF authentication class.
# """


# class ClerkAuthentication(BaseAuthentication):
#     def authenticate(self, request):
#         auth = request.headers.get("Authorization")

#         if not auth or not auth.startswith("Bearer "):
#             return None  # DRF will treat as unauthenticated

#         token = auth.split(" ", 1)[1]

#         try:
#             req_state = authenticate_request(
#                 request,
#                 AuthenticateRequestOptions(
#                     secret_key=os.environ.get("CLERK_SECRET_KEY"),
#                 ),
#             )

#             if not req_state.is_signed_in:
#                 raise AuthenticationFailed("Clerk authentication failed")

#             # register or get user
#             with Clerk(bearer_auth=os.environ.get("CLERK_SECRET_KEY")) as clerk:
#                 user_data = clerk.users.get(user_id=req_state.payload["sub"])
#                 primary_email_id = user_data.primary_email_address_id
#                 user_email = next(
#                     (
#                         email.email_address
#                         for email in user_data.email_addresses
#                         if email.id == primary_email_id
#                     ),
#                     None,
#                 )

#                 if user_email is None:
#                     raise AuthenticationFailed("Clerk user has no email")

#                 user, _ = User.objects.get_or_create(
#                     username=req_state.payload["sub"],
#                     defaults={
#                         "email": user_email,
#                         "first_name": user_data.first_name or "",
#                         "last_name": user_data.last_name or "",
#                         "is_active": True,
#                         "is_staff": False,
#                         "last_login": timezone.now(),
#                     },
#                 )
#                 return (user, None)
#         except AuthenticationFailed:
#             # Re-raise authentication failures
#             raise
#         except Exception as e:
#             # Log unexpected errors and raise authentication failed
#             logger.error(f"Clerk authentication error: {str(e)}", exc_info=True)
#             raise AuthenticationFailed("Authentication failed")
