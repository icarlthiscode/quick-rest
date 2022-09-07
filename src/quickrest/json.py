from json import loads as load_json

from django.http import JsonResponse, HttpRequest
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

    badRequest = error_dict(400, 'Bad request')
    badMethod = error_dict(400, 'Invalid request method')
    malformedBody = error_dict(400, 'Malformed request body')
    unauthorized = error_dict(401, 'Unauthorized request')
    alreadyExists = error_dict(403, 'Resource already exists')
    notFound = error_dict(404, 'Resource not found')
    badCsvFile = error_dict(415, 'Could not import CSV file')
    serverError = error_dict(500, 'Could not process request')

    def __init__(self, code: int, msg: str):
        super().__init__()
        self.update(error_dict(code, msg))

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
        body.update(JsonError.malformedBody)
        return False

class JsonView(View):
    """A view template accepting and returning JSON notation.

    Attributes:
        json_body:
            A dictionary of JSON fields extracted from incoming request.
    """

    json_body: dict = None

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:

        self.json_body = {}
        # try and load json objects only if request not empty
        if (request.body
                and not try_load_json_request(request, self.json_body)):
            return JsonResponse(self.json_body)

        response = super().dispatch(request, *args, **kwargs)

        return JsonResponse(response)
