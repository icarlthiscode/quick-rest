from django.http import HttpRequest
from django.db import models

from .json import JsonError, JsonView
from .log import capture_error, log
from .model import IntegrityError, ModelError, get_fields, ValidationError

class ConfigError(Exception):
    """An invalid API configuration was encountered.
    """

class DeserializationError(Exception):
    """JSON could not be deserialized.
    """

class ApiView(JsonView):
    """An extended Django view abstraction for REST-Like API implementation.
    """

    model = None

    visible_fields = None
    strict_fields = True

    def serialize(self, model_fields: dict) -> dict:
        """Serialize model fields into JSON dictionary.

        Should be overridden to cutomize JSON serialization.

        Args:
            model_fields:
                Model field dictionary to be converted for JSON serialization

        Returns:
            Serialized JSON dictionary.
        """

        return model_fields

    def deserialize(self, json_fields: dict) -> dict:
        """Deserialize model fields from JSON dictionary.

        Should be overridden to cutomize JSON deserialization.

        Args:
            json_fields:
                JSON field dictionary to be converted for JSON deserialization

        Returns:
            Deserialized model field dictionary.
        """

        return json_fields

    def serialize_model(self, model: models.Model) -> dict:
        """Serialize model instance to JSON.

        Args:
            The model to be serialized.

        Returns:
            The serialized model.

        Raises:
            ConfigError:
                Visible fields are not defined.
            ModelError:
                Model field specified in visible_fields does not exist.
        """

        if not self.visible_fields:
            raise ConfigError('Attribute visible_fields must be defined.')
        return self.serialize(
            get_fields(model, self.visible_fields, self.strict_fields)
        )

    def check_model(self):
        """Verify model is defined.

        Raises:
            ConfigError:
                Model is not defined.
        """

        if not self.model:
            raise ConfigError('Attribute visible_fields must be defined.')

    def create_model(self, **fields) -> models.Model:
        """Create new model instance with inital field values.

        Args:
            **fields:
                A set of named arguments specifying model the attributes values
                to initialize with.

        Returns:
            The newly created model instance.

        Raises:
            ModelError:
                An error occurred setting a model attributes.
            ValidationError:
                Attribute values are invalid.
        """

        self.check_model()
        return self.model.create(**fields)

    def retrieve_all_models(self):
        """Query database for all associated models.

        Returns:
            A QuerySet generated from objects.all().
        """

        self.check_model()
        return self.model.objects.all()

    def retrieve_model_by_key(self, key):
        """Query database for model by primary key.

        Args:
            Primary key to query.

        Returns:
            The matching model instance.

        Raise:
            ValueError:
                Model instance not found.
        """

        self.check_model()
        try:
            return self.retrieve_all_models().get(pk = key)
        except self.model.DoesNotExist:
            raise ValueError('Invalid primary key.')

    def update_model(self, model, **fields):
        """Update and save model with new field values.

        Args:
            **fields:
                A set of named arguments specifying attributes to be changed.
        Returns:
            The newly created model instance.

        Raises:
            ModelError:
                An error occurred setting a model attribute.
            ValidationError:
                Attribute values are invalid.
        """

        return model.update(**fields)

    def delete_model(self, model):
        """Delete model instance from database.

        Raises:
            Integrity Error:
                Deletion of instance would violate database integrity.
        """

        try:
            model.delete()
        except IntegrityError as e:
            raise IntegrityError(
                f'Could not delete {self.model.model_name_verbose}'
            ) from e

    def get(self, request: HttpRequest, key = None):

        if key:
            try:
                obj = self.retrieve_model_by_key(key)
            except ValueError:
                log('Resource not found')
                return JsonError.not_found

            try:
                return {self.model.model_name :
                    self.serialize_model(obj)
                }
            except (ConfigError, ModelError) as e:
                capture_error(e)
                return JsonError.serverError

        objs = self.retrieve_all_models()
        try:
            return {f'{self.model.model_name}s' :
                {i.pk : self.serialize_model(i) for i in objs}
            }
        except (ConfigError, ModelError) as e:
            capture_error(e)
            return JsonError.serverError

    def post(self, request: HttpRequest, key = None):

        try:
            json = self.json_body[self.model.model_name]
        except KeyError:
            log('No resource data provided')
            return JsonError.badRequest

        try:
            json = self.deserialize(json)
        except DeserializationError as e:
            capture_error(e)
            return JsonError.server_error

        if key:
            try:
                obj = self.retrieve_model_by_key(key)
                obj = self.update_model(obj, **json)
            except ValueError:
                log('Resource not found')
                return JsonError.notFound
            except ModelError as e:
                capture_error(e)
                return JsonError.badRequest

        else:
            try:
                obj = self.create_model(**json)
            except (ModelError, ValidationError) as e:
                capture_error(e)
                return JsonError.badRequest

        try:
            return {self.model.model_name :
                self.serialize_model(obj)
            }
        except (ConfigError, ModelError) as e:
            capture_error(e)
            return JsonError.serverError

    def delete(self, request: HttpRequest, key = None):

        if not key:
            log('No resource key provided')
            return JsonError.badRequest

        try:
            obj = self.retrieve_model_by_key(key)
        except ValueError:
            log('Resource not found')
            return JsonError.notFound

        try:
            self.delete_model(obj)
            return {'success' : True}
        except IntegrityError as e:
            capture_error(e)
            return JsonError.server_error
