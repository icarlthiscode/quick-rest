from typing import Any, Union, Generic, TypeVar

from django.db.models import QuerySet
from django.http import HttpRequest

from .http import (
    HttpError,
    RequestError,
    NotFoundError,
    ServerError,
    ConfigError,
)
from .json import JsonError, JsonView, JsonResponse
from .log import EVENT_TYPE, capture_error, error
from .models import (
    IntegrityError,
    ModelError,
    ValidationError,
    Model,
    get_fields,
)

Json = dict[str, Union[None, int, str, bool]]
Json = dict[str, Union[None, int, str, bool, list[Json], dict[str, Json]]]

MT = TypeVar('MT', bound = Model)

class ApiView(JsonView, Generic[MT]):
    """An extended Django view abstraction for REST-Like API implementation.
    """

    model : MT = None

    visible_fields = None
    strict_fields = True

    primary_key = None
    query = None
    json = None

    def read_query(self, **kwargs) -> dict[str, str]:
        """Read query params from request.

        Args:
            **kwargs:
                Dispatch kwargs to used when reading query params.
        """

        return self.query_params

    def read_json(self, **kwargs) -> Json:
        """Read resource data from request.

        Args:
            **kwargs:
                Dispatch kwargs to used when reading JSON data.
        """

        try:
            return self.json_body[self.model.model_name()]
        except KeyError:
            return None

    def serialize(self, model_fields: dict) -> Json:
        """Serialize model fields into JSON dictionary.

        Should be overridden to cutomize JSON serialization.

        Args:
            model_fields:
                Model field dictionary to be converted for JSON serialization

        Returns:
            Serialized JSON dictionary.

        Raises:
            SerializationError:
                A resource model could not be serialized.
        """

        return model_fields

    def deserialize(self, json_fields: dict) -> dict[str, Any]:
        """Deserialize model fields from JSON dictionary.

        Should be overridden to cutomize JSON deserialization.

        Args:
            json_fields:
                JSON field dictionary to be converted for JSON deserialization

        Returns:
            Deserialized model field dictionary.

        Raises:
            DeserializationError:
                Resource JSON could not be deserialized.
        """

        return json_fields

    def serialize_model(self, model: Model) -> Json:
        """Serialize model instance to JSON.

        Args:
            The model to be serialized.

        Returns:
            The serialized model.

        Raises:
            ConfigError:
                Model is not defined.
            ServerError:
                An unexpected error was encountered.
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

    def validate_model(self, **fields) -> MT:
        """Validate a model instance with initial field values.

        Args:
            **fields:
                A set of named arguments specifying model the attributes values
                to initialize with.

        Returns:
            The newly created model instance.

        Raises:
            RequestError:
                The request is invalid.
        """

        self.check_model()
        try:
            model = self.model.new(**fields)
            model.full_clean()
        except (ModelError, ValidationError) as e:
            raise RequestError(
                f'Invalid {self.model.model_name_verbose} data'
            ) from e

        return model

    def create_model(self, **fields) -> MT:
        """Create new model instance with inital field values.

        Args:
            **fields:
                A set of named arguments specifying model the attributes values
                to initialize with.

        Returns:
            The newly created model instance.

        Raises:
            RequestError:
                The request is invalid.
            ServerError:
                An unexpected error was encountered.
        """

        self.check_model()
        try:
            return self.model.create(**fields)
        except (ModelError, ValidationError) as e:
            raise RequestError(
                f'Invalid {self.model.model_name_verbose()} data'
            ) from e

    # TODO: improve QuerySet typing
    def retrieve_all_models(self, **params) -> Union[QuerySet, list[MT]]:
        """Query database for all associated models.

        Returns:
            A QuerySet generated from objects.all().

        Raises:
            RequestError:
                The request is invalid.
            ServerError:
                An unexpected error was encountered.
        """

        self.check_model()
        return self.model.objects.all()

    def retrieve_model_by_key(self, key, **params) -> MT:
        """Query database for model by primary key.

        Args:
            Primary key to query.

        Returns:
            The matching model instance.

        Raises:
            RequestError:
                The request is invalid.
            ServerError:
                An unexpected error was encountered.
        """

        self.check_model()
        try:
            return self.retrieve_all_models().get(pk = key)
        except self.model.DoesNotExist:
            raise NotFoundError('Resourse not found.')

    def update_model(self, model, **fields) -> MT:
        """Update and save model with new field values.

        Args:
            **fields:
                A set of named arguments specifying attributes to be changed.
        Returns:
            The newly created model instance.

        Raises:
            RequestError:
                The request is invalid.
            ServerError:
                An unexpected error was encountered.
        """

        try:
            return model.update(**fields)
        except (ModelError, ValidationError) as e:
            raise RequestError('Invalid POST data') from e

    def delete_model(self, model):
        """Delete model instance from database.

        Raises:
            RequestError:
                The request is invalid.
            ServerError:
                An unexpected error was encountered.
        """

        try:
            model.delete()
        except IntegrityError as e:
            raise RequestError(
                f'Cannot delete {self.model.model_name_verbose()} ({model.pk})'
            ) from e

    def return_model(self, obj : Model, **keys) -> Json:
        """Return model instance in serialized JSON format.

        Returns:
            A JSON formated dictionary of the serialized model instance.

        Raises:
            ServerError:
                An unexpected error was encountered.
        """

        return { self.model.model_name() : self.serialize_model(obj) }

    def return_models(self, objs : list[Model], **keys) -> Json:
        """Return a list of model instances in serialized JSON format.

        Returns:
            A JSON formated dictionary of the serialized model instances.

        Raises:
            ServerError:
                An unexpected error was encountered.
        """

        return { f'{self.model.model_plural_name()}' :
            { i.pk : self.serialize_model(i) for i in objs }
        }

    def get(self, request: HttpRequest, **keys):
        if self.primary_key:
            obj = self.retrieve_model_by_key(
                self.primary_key,
                **self.query_params,
            )
            return self.return_model(obj, **keys)

        else:
            objs = self.retrieve_all_models(**self.query_params)
            return self.return_models(objs, **keys)

    def post(self, request: HttpRequest, **keys):
        if self.primary_key:
            return JsonError.bad_method

        json = self.read_json(**keys)
        fields = self.deserialize(json)

        obj =  self.create_model(**fields)

        return self.return_model(obj, **keys)

    def put(self, request: HttpRequest, **keys):
        if not self.primary_key:
            return JsonError.bad_method

        json = self.read_json(**keys)
        fields = self.deserialize(json)

        obj = self.retrieve_model_by_key(**keys)
        self.validate_model(**fields)
        obj = self.update_model(obj, **fields)

        return self.return_model(obj, **keys)

    def delete(self, request: HttpRequest, **keys):
        if not self.primary_key:
            raise RequestError(
                'No resource key provided',
                request = request,
            )

        obj = self.retrieve_model_by_key(self.primary_key)
        self.delete_model(obj)

        return { 'success' : True }

    def post_load(self, request, *args, **kwargs):
        self.primary_key = kwargs.get('key')
        self.query = self.read_query(**kwargs)
        self.json = self.read_json(**kwargs)

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except HttpError as e:
            if isinstance(e, ServerError):
                capture_error(e)
            else:
                error(
                    str(e),
                    event_type = EVENT_TYPE.http,
                    request = e.request,
                )
            return JsonResponse(JsonError.from_code(e.status_code))
