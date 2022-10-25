import requests

from .log import capture_error

class ConfigError(Exception):
    """An invalid webhook configuration was encountered.
    """

class Hook:
    """An abstract class for generating webhook events.
    """

    @classmethod
    def serialize(cls, **kwargs) -> dict:
        """Serialize event payload into JSON dict.

        Args:
            **kwargs:
                Additional keyword webhook event arguments.

        Returns:
            The serialized payload.
        """

        return kwargs

    @classmethod
    def deserialize(cls, response: requests.Response, *args, **kwargs) -> dict:
        """Deserialize webhook response into JSON dict.

        Args:
            response:
                The returned HTTP reponse.
            *args:
                Additional positional webhook event arguments.
            **kwargs:
                Additional keyword webhook event arguments.

        Returns:
            The deserialized response.

        Raises:
            ValueError:
                Response JSON could not be deserialized.
        """

        return response.json()

    @classmethod
    def callback(cls, result: dict, *args, **kwargs) -> None:
        """The action to be called following a webhook response.

        Args:
            result:
                The returned JSON response.
            *args:
                Additional positional webhook event arguments.
            **kwargs:
                Additional keyword webhook event arguments.
        """

        pass

    def call(self, payload: dict, *arg, **kwargs) -> requests.Response:
        """Make a webhook endpoint request.

        Args:
            payload:
                A JSON dict to be used as the request payload.
            *args:
                Additional positional webhook event arguments.
            **kwargs:
                Additional keyword webhook event arguments.

        Returns:
            The HTTP response from the webhook endpoint.

        Raises:
            ConfigError:
                The webhook URL is not defined.

        """

        try:
            return requests.post(self.url, json = payload)
        except AttributeError as e:
            capture_error(e)
            raise ConfigError('Webhook endpoint is not defined') from e

    def fire(self, *args, **kwargs) -> dict:
        """Fire webhook event.

        Args:
            *args:
                Positional event arguments.
            **kwargs:
                Keyword event arguements.

        Returns:
            The deserialized response from the webhook endpoint.

        Raises:
            RuntimeError:
                The response from the webhook enpoint could not be interpreted.
        """

        payload = self.serialize(**kwargs)

        response = self.call(payload, *args, **kwargs)

        try:
            result = self.deserialize(response, *args, **kwargs)
        except ValueError as e:
            capture_error(e)
            raise RuntimeError('Response could not be interpreted')

        self.callback(result, *args, **kwargs)

        return result
