import json
from typing import Any, Dict

from django.http import HttpRequest, HttpResponse

class Reasons:
    bad_request = 'badRequest'
    invalid_field = 'invalidField'
    no_key = 'noKey'
    integrity_error = 'integrityError'
    not_found = 'notFound'
    server_error = 'serverError'
    config_error = 'configError'
    serialization_error = 'serializationError'
    deserialization_error = 'deserializationError'

class HttpError(RuntimeError):
    """An error was encountered during an HTTP request.
    """
    status_code = 500

    def __init__(
        self,
        *args,
        request : HttpRequest = None,
        reason : str = '',
        **kwargs,
    ):
        self.request = request
        if reason: self.reason = reason

class RequestError(HttpError):
    """Invalid request.
    """
    status_code = 400
    reason = Reasons.bad_request

class NotFoundError(HttpError):
    """Resource not found.
    """
    status_code = 404
    reason = Reasons.not_found

class ServerError(HttpError):
    """An unexpected error was encountered.
    """
    status_code = 500
    reason = Reasons.server_error

class SerializationError(ServerError):
    """Model could not be serialized.
    """
    reason = Reasons.serialization_error

class DeserializationError(RequestError):
    """Request data could not be deserialized.
    """
    reason = Reasons.deserialization_error

class ConfigError(ServerError):
    """An invalid API configuration was encountered.
    """
    reason = Reasons.config_error

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
