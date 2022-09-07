from django.http import HttpRequest
from django.db import models

from .json import JsonError, JsonView
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

    @classmethod
    def serialize(cls, model_fields: dict) -> dict:
        """Serialize model fields into JSON dictionary.

        Should be overridden to cutomize JSON serialization.

        Args:
            model_fields:
                Model field dictionary to be converted for JSON serialization

        Returns:
            Serialized JSON dictionary.
        """
        
        return model_fields

    @classmethod
    def deserialize(cls, json_fields: dict) -> dict:
        """Deserialize model fields from JSON dictionary.

        Should be overridden to cutomize JSON deserialization.

        Args:
            json_fields:
                JSON field dictionary to be converted for JSON deserialization

        Returns:
            Deserialized model field dictionary.
        """

        return json_fields

    @classmethod
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

    @classmethod
    def check_model(cls):
        """Verify model is defined.
        
        Raises:
            ConfigError:
                Model is not defined.
        """

        if not cls.model:
            raise ConfigError('Attribute visible_fields must be defined.')
    
    @classmethod
    def create_model(cls, **fields) -> models.Model:
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

        cls.check_model()
        return cls.model.create(**fields)

    @classmethod
    def retrieve_all_models(cls):
        """Query database for all associated models.

        Returns:
            A QuerySet generated from objects.all().
        """

        cls.check_model()
        return cls.model.objects.all()

    @classmethod
    def retrieve_model_by_key(cls, key):
        """Query database for model by primary key.

        Args:
            Primary key to query.

        Returns:
            The matching model instance.

        Raise:
            ValueError:
                Model instance not found.
        """

        cls.check_model()
        try:
            return cls.model.objects.get(pk = key)
        except cls.model.DoesNotExist:
            raise ValueError('Invalid primary key.')

    @classmethod
    def update_model(cls, model, **fields):
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

    @classmethod
    def delete_model(cls, model):
        """Delete model instance from database.

        Raises:
            Integrity Error:
                Deletion of instance would violate database integrity.
        """

        try:
            model.delete()
        except IntegrityError as e:
            raise IntegrityError(
                f'Could not delete {cls.model.model_name_verbose}'
            ) from e

    def get(self, request: HttpRequest, key = None):

        if key:
            try:
                obj = self.retrieve_model_by_key(key)
            except ValueError:
                return JsonError.badRequest

            try:
                return {self.model.model_name :
                    self.serialize_model(obj)
                }
            except (ConfigError, ModelError):
                return JsonError.serverError

        objs = self.retrieve_all_models()
        try:
            return {f'{self.model.model_name}s' :
                {i.pk : self.serialize_model(i) for i in objs}
            }
        except (ConfigError, ModelError):
            return JsonError.serverError

    def post(self, request: HttpRequest, key = None):

        try:
            json = self.json_body[self.model.model_name]
        except KeyError:
            return JsonError.badRequest
        
        try:
            json = self.deserialize(json)
        except DeserializationError:
            return JsonError.badRequest
        except:
            return JsonError.serverError

        if key:
            try:
                obj = self.retrieve_model_by_key(key)
                obj = self.update_model(obj, **json)
            except ValueError:
                return JsonError.notFound
            except (ModelError, ValueError):
                return JsonError.badRequest

        else:
            try:
                obj = self.create_model(**json)
            except (ModelError, ValidationError):
                return JsonError.badRequest

        try:
            return {self.model.model_name :
                self.serialize_model(obj)
            }
        except (ConfigError, ModelError) as e:
            return JsonError.serverError

    def delete(self, request: HttpRequest, key = None):

        if not key:
            return JsonError.badRequest

        try:
            obj = self.retrieve_model_by_key(key)
        except ValueError:
            return JsonError.notFound

        try:
            self.delete_model(obj)
            return {'success' : True}
        except IntegrityError:
            return JsonError.badRequest
