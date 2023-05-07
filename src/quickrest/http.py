import json
from typing import Any, Dict

from django.http import HttpRequest, HttpResponse

class HttpError(RuntimeError):
    """An error was encountered during an HTTP request.
    """
    status_code = 500

    def __init__(self, *args, request : HttpRequest = None, **kwargs):
        self.request = request

class RequestError(HttpError):
    """Invalid request.
    """
    status_code = 400

class NotFoundError(HttpError):
    """Resource not found.
    """
    status_code = 404

class ServerError(HttpError):
    """An unexpected error was encountered.
    """
    status_code = 500

class SerializationError(ServerError):
    """Model could not be serialized.
    """

class DeserializationError(RequestError):
    """Request data could not be deserialized.
    """

class ConfigError(ServerError):
    """An invalid API configuration was encountered.
    """

def serialize_request(request : HttpRequest) -> Dict[str, Any]:
    try:
        body = json.loads(request.body)
    except ValueError:
        body = request.body

    return {
        'headers' : request.headers,
        'body' : body,
    }

def serialize_response(response : HttpResponse) -> Dict[str, Any]:
    try:
        body = json.loads(response.content.decode())
    except ValueError:
        body = response.content.decode()

    return {
        'body' : body,
    }
