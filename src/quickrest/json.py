from json import loads as load_json

from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse as DjangoJsonResponse,
)
from django.views import View

GET = 'GET'
POST = 'POST'
DELETE = 'DELETE'

ACCEPTED_METHODS_ATTR = 'accepted_methods'

def error_dict(code: int, msg: str) -> dict:
    """Generate dictionary items for error JSON.

    Args:
        code:
            Assosicated error code.
        msg:
            Discription of error and context.

    Returns:
        Dictionary containing error json fields.
    """
    return {
        'error' : {
            'code' : code,
            'message' : msg
        }
    }

class JsonError(dict):
    """A class for generating JSON error responses.

    Attributes:
        code:
            Assosicated error code.
        msg:
            Discription of error and context.
    """

    bad_request = error_dict(400, 'Bad request')
    malformed_body = error_dict(400, 'Malformed request body')
    unauthorized = error_dict(401, 'Unauthorized request')
    already_exists = error_dict(403, 'Resource already exists')
    not_found = error_dict(404, 'Resource not found')
    bad_method = error_dict(405, 'Invalid request method')
    bad_csv_file = error_dict(415, 'Could not import CSV file')
    server_error = error_dict(500, 'Could not process request')

    @classmethod
    def from_code(cls, code) -> dict:
        if code == 400: return cls.bad_request
        if code == 401: return cls.unauthorized
        if code == 403: return cls.already_exists
        if code == 404: return cls.not_found
        if code == 405: return cls.bad_method
        if code == 500: return cls.server_error

    def __init__(self, code: int, msg: str):
        super().__init__()
        self.update(error_dict(code, msg))

class JsonResponse(DjangoJsonResponse):

    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)

        if ('status' not in kwargs) and data and ('error' in data):
            if 'code' in data['error']: self.status_code = data['error']['code']

def load_json_request(request: HttpRequest) -> dict:
    """Extract json fields from request body.

    Args:
        request:
            A recieved HTTP request object.

    Returns:
        A dictionary representation of the JSON body.

    Raises:
        ValueError:
            Unable to parse Json body.
    """

    body = load_json(request.body)
    return body

def try_load_json_request(request: HttpRequest, body: dict = None) -> bool:
    """Extract json fields from request body.

    Args:
        request:
            A recieved HTTP request object.
        body:
            A dictionary instance that will store the extracted fields.

    Returns:
        Whether the extraction of JSON fields was successful.
    """

    try:
        body.update(load_json_request(request))
        return True
    except:
        body.update(JsonError.malformed_body)
        return False

class JsonView(View):
    """A view template accepting and returning JSON notation.

    Attributes:
        json_body:
            A dictionary of JSON fields extracted from incoming request.
    """

    json_body : dict = None
    query_params : dict = None

    def post_load(self, request: HttpRequest, *args, **kwargs):
        """Hook for defining for logic after request has been loaded, but before
        request has been dispatched.

        Args:
            request:
                A recieved HTTP request object.
            *args:
                Additional positional arguments.
            **kwargs:
                Additional keyword arguments.
        """

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:

        self.json_body = {}
        self.query_params = request.GET.dict() if request.GET else {}

        # try and load json objects only if request not empty
        if (request.body
                and not try_load_json_request(request, self.json_body)):
            return JsonResponse(JsonError.bad_request)

        self.post_load(request, *args, **kwargs)
        response = super().dispatch(request, *args, **kwargs)

        if isinstance(response, HttpResponse): return response
        else: return JsonResponse(response)
