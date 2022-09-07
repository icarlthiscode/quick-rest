from __future__ import annotations
from tabnanny import verbose
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.utils.functional import classproperty

class ModelError(Exception):
    """An error associated with model field evaluation and assignment.
    """

    pass

def get_fields(
        model: models.Model, field_names, fail_missing = False
    ) -> dict[str, Any]:
    """Create dictionary from a Django model.

    Args:
        model:
            A django model instance to evaluate.
        field_names:
            A list of field name strings to evaluate.
        fail_missing:
            Whether missing

    Raise:
        ModelError:
            Expected model field is not defined.
    """

    fields = {}
    for fn in field_names:
        if not (hasattr(model, fn) or fail_missing):
            continue
            
        try:
            fields[fn] = getattr(model, fn)
        except AttributeError as e:
            raise ModelError(f'Required field {fn} not found') from e

    return fields

class ModelError(Exception):
    """An error associated with model field assignment.
    """

    pass

class Model(models.Model):
    """An extended Django model abstraction with added validation functionality.
    """

    # TODO: improve resole config attribute efficiency 
    
    class Config:
        """Class for defining model configuration.
        """

        pass

    class BaseConfig:
        """Defuat model configuration.
        """

        name = 'model'
        mutable_fields = None

    class Meta:
        abstract = True

    @classproperty
    def model_name(cls) -> str:
        try:
            return cls.Config.name
        except AttributeError:
            return cls.BaseConfig.name

    @classproperty
    def model_name_verbose(cls) -> str:
        try:
            return cls.Config.verbose_name
        except AttributeError:
            try:
                return cls.Config.name
            except AttributeError:
                return cls.BaseConfig.name
        
    @classproperty
    def model_mutable_fields(cls) -> str:
        try:
            return cls.Config.mutable_fields
        except AttributeError:
            return cls.BaseConfig.mutable_fields

    @classmethod
    def new(cls, **kwargs) -> Model:
        """Create new model instance without commiting to database.

        Args:
            **kwargs:
                A set of named arguments specifying model the attributes to
                initialize with.  

        Returns:
            The newly created model instance.
        
        Raises:
            ModelError:
                An error occurred setting a model attributes.
        """
        
        try:
            return cls(**kwargs)
        except TypeError as e:
            raise ModelError(
                f'Invalid assignment during {cls.model_name_verbose} creation'
            ) from e

    @classmethod
    def create(cls, **kwargs) -> Model:
        """Create new model instance and commit model to database.

        Args:
            **kwargs:
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

        inst = cls.new(**kwargs)

        try:
            inst.full_clean()
        except ValidationError as e:
            raise ValidationError(
                f'Invalid {cls.model_name_verbose} parameters'
            ) from e

        inst.save()
        return inst

    def update(self, **kwargs) -> None:
        """Update model instance and commit model to database.

        Update model attributes, validate, and save model. If
        self.mutable_fields is set, only attributes matching the strings in
        mutable_fields are updated, all others are ignored.  

        Args:
            **kwargs:
                A set of named arguments specifying attributes to be changed.

        Returns:
            The newly created model instance.

        Raises:
            ModelError:
                An error occurred setting a model attribute.
            ValidationError:
                Attribute values are invalid.
        """

        try:
            for kw in kwargs:
                if kw in self.model_mutable_fields:
                    setattr(self, kw, kwargs[kw])

            self.full_clean()
        except (ValueError, TypeError) as e:
            raise ModelError(
                f'Invalid attribute during {self.model_name_verbose} update'
            ) from e
        except ValidationError as e:
            raise ValidationError(
                f'Invalid attribute during {self.model_name_verbose} update'
            ) from e

        self.save()

    def delete(self, *args, **kwargs) -> None:
        """Delete model instance from database.

        Raises:
            Integrity Error:
                Deletion of instance would violate database integrity.
        """

        try:
            super().delete(*args, **kwargs)
        except IntegrityError as e:
            raise IntegrityError(
                f'Could not delete {self.model_name_verbose}'
            ) from e
