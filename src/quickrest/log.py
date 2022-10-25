from django.conf import settings

def capture_error(exception):
    """Report a rasied exception using configured logging function

    The exception is passed to the loggin function configured in the Django
    settings field QUICKREST_CAPTURE, accepting the exception as the only
    positional argument.

    Args:
        exception:
            The exception to report.
    """

    try:
        handle_error = settings.QUICKREST_CAPTURE
        handle_error(exception)
    except NameError as e:
        pass

def error(msg: str):
    """Report an error message with configured logging function

    The error message is passed to the loggin function configured in the Django
    settings field QUICKREST_ERROR, accepting the error message as the only
    positional argument.

    Args:
        msg:
            The error message to report.
    """

    try:
        handle_error = settings.QUICKREST_ERROR
        handle_error(msg)
    except NameError as e:
        pass
