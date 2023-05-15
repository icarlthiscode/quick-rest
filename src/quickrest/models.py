from __future__ import annotations
from typing import Any, Union

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.db.models import Field, ForeignObjectRel

class ModelError(AttributeError):
    """An error associated with model field evaluation and assignment.
    """

class Model(models.Model):
    """An extended Django model abstraction with added validation functionality.
    """

    class QuickConfig:
        """Class for defining quickrest model configuration.
        """

    # TODO: improve resolve of default config attribute efficiency
    class BaseQuickConfig:
        """Defualt quickrest model configuration.
        """

        name = 'model'
        mutable_fields = None
        serializable_fields = None

    class Meta:
        abstract = True

    @classmethod
    def model_name(cls) -> str:
        try:
            return cls.QuickConfig.name
        except AttributeError:
            return cls.BaseQuickConfig.name

    @classmethod
    def model_plural_name(cls) -> str:
        try:
            if hasattr(cls.QuickConfig, 'plural_name'):
                return cls.QuickConfig.plural_name
            else: return cls.QuickConfig.name + 's'
        except AttributeError:
            return cls.BaseQuickConfig.name

    @classmethod
    def model_name_verbose(cls) -> str:
        try:
            return cls.QuickConfig.verbose_name
        except AttributeError:
            try:
                return cls.QuickConfig.name
            except AttributeError:
                return cls.BaseQuickConfig.name

    @classmethod
    def model_mutable_fields(cls) -> str:
        try:
            return cls.QuickConfig.mutable_fields
        except AttributeError:
            return cls.BaseQuickConfig.mutable_fields

    @classmethod
    def model_serializable_fields(cls) -> str:
        try:
            return cls.QuickConfig.serializable_fields
        except AttributeError:
            return cls.BaseQuickConfig.serializable_fields

    @classmethod
    def get_model_fields(cls) -> list[Union[Field, ForeignObjectRel]]:
        """List the names of configured Django model fields.
        """
        return cls._meta.get_fields()

    @classmethod
    def filter_fields(cls, **kwargs) -> dict:
        return kwargs.copy()

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
            return cls(**cls.filter_fields(**kwargs))
        except TypeError as e:
            raise ModelError(
                f'Invalid assignment during {cls.model_name_verbose()} creation'
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
                f'Invalid {cls.model_name_verbose()} parameters'
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

        filtered_kwargs = self.filter_fields(**kwargs)

        try:
            for kw, arg in filtered_kwargs.items():
                if kw in self.model_mutable_fields():
                    setattr(self, kw, arg)

            self.full_clean()
        except (ValueError, TypeError) as e:
            raise ModelError(
                f'Invalid attribute during {self.model_name_verbose()} update'
            ) from e
        except ValidationError as e:
            raise ValidationError(
                f'Invalid attribute during {self.model_name_verbose()} update'
            ) from e

        self.save()
        return self

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
                f'Could not delete {self.model_name_verbose()}'
            ) from e

    def raw(self) -> dict[str, Any]:
        """Return raw model data.

        Returns:
            A dictionary of model attributes and values.
        """

        field_names = self.model_serializable_fields()
        if field_names is None:
            field_names = self.get_model_fields()
            field_names = [f.name for f in field_names]

        return {
            fn : getattr(self, fn) for fn in field_names
                for fn in field_names
        }
