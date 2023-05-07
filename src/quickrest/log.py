import logging

from django.http import HttpRequest, HttpResponse

from .json import JsonError, JsonResponse

LOGGER_NAME = 'quickrest'

class EVENT_LEVEL:
    debug = logging.DEBUG
    info = logging.INFO
    warning = logging.WARNING
    error = logging.ERROR
    critical = logging.CRITICAL

class EVENT_TYPE:
    default = 'DEFAULT'
    exception = 'EXCEPTION'
    auth = 'AUTH'
    http = 'HTTP'

def get_logger() -> logging.Logger:
    """Get the quickrest logger.

    Returns:
        The quickrest logger.
    """

    logger = logging.getLogger(LOGGER_NAME)
    if not logger.hasHandlers():
        logger.addHandler(logging.NullHandler())

    return logger

def log(
    msg: str,
    event_level : int = EVENT_LEVEL.info,
    event_type : str = EVENT_TYPE.default,
    request : HttpRequest = None,
    response : HttpResponse = None,
    **data
):
    """Log a record to the quickrest logger.

    Args:
        msg:
            The message to report.
        event_level:
            The logging level of the event.
        event_type:
            The event type used to categories events configured logging
            function.
        request:
            The incoming HTTP request.
        response:
            The outgoing HTTP response.
        **data:
            Any additional information to be set with the record.
    """

    logger = get_logger()
    logger.log(
        level = event_level,
        msg = msg,
        extra = {
            'event_type' : event_type,
            **({'request' : request} if request else {}),
            **({'response' : response} if response else {}),
            **data,
        }
    )

def error(
    msg : str,
    event_type : str = EVENT_TYPE.default,
    request : HttpRequest = None,
    response : HttpResponse = None,
    **data
):
    """Log a error to the quickrest logger.

    Args:
        msg:
            The message to report.
        event_type:
            The event type used to categories events configured logging
            function.
        request:
            The incoming HTTP request.
        response:
            The outgoing HTTP response.
        **data:
            Any additional information to be set with the record.
    """

    log(
        msg = msg,
        event_level = EVENT_LEVEL.error,
        event_type = event_type,
        request = request,
        response = response,
        **data,
    )

def capture_error(e : Exception):
    """Log a rasied exception.

    Args:
        exception:
            The exception to be logged.
    """

    error(msg = str(e), event_type = EVENT_TYPE.exception)

class Middleware:
    """Django middleware for monitoring responses and requests.
    """

    def __init__(self, get_response):

        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except RuntimeError as e:
            capture_error(e)
            response = JsonResponse(JsonError.server_error)

        log(
            'Response successful',
            event_type = EVENT_TYPE.http,
            request = request,
            response = response,
        )

        return response
