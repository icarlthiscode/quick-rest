from typing import Callable, Dict, List

import random
import string
from functools import wraps

import jwt

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.utils.decorators import decorator_from_middleware, method_decorator

from .json import JsonError, JsonResponse
from .log import EVENT_TYPE, error

User = get_user_model()

class AuthError(Exception):
    pass

AUTH_EXEMPT_ATTR = 'auth_exempt'
AUTH_METHOD_ATTR = 'auth_method'
REQ_PERM_ATTR = 'required_permissions'

class AuthInfo:
    """A structured representation of request authorization information.
    """

    _user = None
    _perm = []

    @property
    def user(self) -> int:
        """The authorized user id.
        """
        return self._user

    @property
    def user_id(self) -> int:
        """The authorized user id.
        """
        return self._user_id

    @property
    def permissions(self) -> List[str]:
        """The authorized user permision list.
        """
        return self._perm

    def has_permission(self, permission: str) -> bool:
        """Check whether authorization includes permission.

        Args:
            permission:
                The permission to be checked.

        Returns:
            Whether the authorization includes the permission.
        """

        return permission in self.permissions

    def __init__(
        self,
        user_id: int,
        permissions: List[str] = None,
        use_user = True
    ):
        """Generate new AuthInfo instance.

        Args:
            user_id:
                The unique id of the authorized user.
            permissions:
                The list of authorized permissions.
            use_user:
                Retrieve user object.
        """

        self._user = User.objects.get(pk = user_id) if use_user else None
        self._user_id = user_id
        self._perm = permissions if permissions else []

def generate_key(length: int) -> str:
    """Generate a random alphanumeric string.

    Args:
        length:
            The length of the returned string.

    Returns:
        The generated random string.
    """

    key = ''
    choices = string.ascii_uppercase + string.digits
    for _ in range(length):
        key += random.SystemRandom().choice(choices)

    return key

def generate_token(payload: dict, key: str = ''):
    """Generate an encoded JWT token.

    Args:
        payload:
            The payload to be encoded.
        key:
            The secret key used to sign the token. Uses JWT_KEY settings
            variable if none provided.

    Returns:
        The generated JWT token.
    """

    k = settings.JWT_KEY if not key else key
    raw_token = jwt.encode(payload, k, algorithm='HS256')
    return raw_token

def verify_token(token: str, key: str = '') -> Dict[str, str]:
    """Verify and decode a JWT token.

    Args:
        payload:
            The payload to be verified and decoded.
        key:
            The secret key used to verify the token. Uses JWT_KEY settings
            variable if none provided.

    Returns:
        The decoded JWT token payload.

    Raises:
        AuthError:
            The JWT token is invalid or can not be decoded.
    """

    k = settings.JWT_KEY if not key else key
    try:
        return jwt.decode(token, k, algorithms='HS256')
    except jwt.exceptions.InvalidSignatureError:
        raise AuthError('Invalid signature')
    except jwt.exceptions.ExpiredSignatureError:
        raise AuthError('Expired token')
    except jwt.exceptions.DecodeError:
        raise AuthError('Malformed token')

def authorize_token(token: str) -> AuthInfo:
    """Convert authorization token into AuthInfo instance.

    Args:
        token:
            The authorization token.

    Returns:
        The AuthInfo instance.

    Raises:
        AuthError:
            The token is invalid.
    """

    try:
        decoded = verify_token(token)
    except AuthError as e:
        raise e

    try:
        return AuthInfo(decoded['sub'], decoded['perm'])
    except:
        raise AuthError('Invalid JWT fields')

def get_bearer_token(request: HttpRequest) -> str:
    """Extract request header bearer token.

    Args:
        request:
            The request to be authorized.

    Raises:
        AuthError:
            No bearer token found.
    """

    header = request.headers.get('Authorization')
    if header is None:
        raise AuthError('No bearer token in request')

    try:
        token = header.split(' ')[1]
    except IndexError as e:
        raise AuthError('Bad bearer token') from e

    return token

def authorize_request(request: HttpRequest) -> None:
    """Authorize a request.

    Args:
        request:
            The request to be authorized.

    Raises:
        AuthError:
            The request is unauthorized.
    """

    header = get_bearer_token(request)

    try:
        auth_type, token = header.split(' ')
    except ValueError:
        raise AuthError('Could not read bearer token')

    if auth_type != 'Bearer':
        raise AuthError(
                str.format('Authorization type not supported: {0}',
                    auth_type))

    try:
        request.auth = authorize_token(token)
    except AuthError as e:
        raise e

def auth_exempt(view_func):
    """Mark functional view as exepmt from authorization.
    """

    # wrap view
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        return view_func(*args, **kwargs)

    # mark new view as exempt
    setattr(wrapped_view, AUTH_EXEMPT_ATTR, True)

    return wrapped_view

auth_exempt_method = method_decorator(auth_exempt)
"""Mark class-view method as exepmt from authorization.
"""

auth_exempt_all = method_decorator(auth_exempt, name="dispatch")
"""Mark class-view as exepmt from authorization.
"""

def auth_override(auth_method: Callable[[HttpRequest], None]):
    """Assign authorization method to a functional view.

    Provided authorization method should raise AuthError if request is
    unauthorized.
    """

    def accepted_method_inner(view_func):
        # wrap view
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            return view_func(*args, **kwargs)

        # mark new view as exempt
        setattr(wrapped_view, AUTH_METHOD_ATTR, auth_method)

        return wrapped_view
    return accepted_method_inner

def auth_override_method(auth_method):
    """Assign authorization method to a class-based view method.

    Provided authorization method should raise AuthError if request is
    unauthorized.
    """

    return method_decorator(auth_override(auth_method))

def auth_override_all(auth_method):
    """Assign authorization method to a class-based view.

    Provided authorization method should raise AuthError if request is
    unauthorized.
    """

    return method_decorator(auth_override(auth_method), name="dispatch")

def permissions_required(permissions: list):
    """Assign required permissions to functional view.
    """

    def accepted_perms(view_func):
        # wrap view
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            return view_func(*args, **kwargs)

        # mark new view as exempt
        setattr(wrapped_view, REQ_PERM_ATTR, permissions)

        return wrapped_view
    return accepted_perms

def permissions_required_all(permissions: list):
    """Assign required permissions to class-based view.
    """

    return method_decorator(
        permissions_required(permissions),
        name='dispatch'
    )

class Middleware:
    """Django middleware for authorizing all incloming requests.
    """

    def process_view(self, request, callback, callback_args, callback_kwargs):

        # check if view is exempt
        if getattr(callback, AUTH_EXEMPT_ATTR, False):
            return None

        # attempt verification
        try:
            auth_method = getattr(callback, AUTH_METHOD_ATTR, None)
            if auth_method: auth_method(request)
            else: authorize_request(request)
        except AuthError:
            # return 401; failed verification will throw error
            error(
                'Unauthorized request',
                event_type = EVENT_TYPE.auth,
                request = request,
            )
            return JsonResponse(JsonError.unauthorized)

        permissions = getattr(callback, REQ_PERM_ATTR, False)
        if permissions:
            for p in permissions:
                if p not in request.auth.permissions:
                    error(
                        'Invalid permissions',
                        event_type = EVENT_TYPE.auth,
                        request = request,
                    )
                    return JsonResponse(JsonError.unauthorized)

    def __init__(self, get_response):

        self.get_response = get_response

    def __call__(self, request):

        return self.get_response(request)

def auth_protect():
    """Enforce authorization of functional view.

    Only to be used if Middleware is not active.
    """

    return decorator_from_middleware(Middleware)

def auth_protect_all():
    """Enforce authorization of class-based view.

    Only to be used if Middleware is not active.
    """

    return method_decorator(auth_protect, name="dispatch")
