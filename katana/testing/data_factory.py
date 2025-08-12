import random
import string
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Type, Optional

from pydantic import BaseModel, EmailStr
from pydantic.fields import FieldInfo


class DataFactory:
    """
    Generates valid and invalid test data sets for a given Pydantic model.
    """

    def __init__(self, model_class: Type[BaseModel]):
        self.model_class = model_class
        self.fields: Dict[str, FieldInfo] = self.model_class.model_fields

    def generate_test_cases(self, total_cases: int = 100) -> List[Dict[str, Any]]:
        """
        Generates a list of test cases, half valid and half invalid.
        """
        if total_cases < 2:
            raise ValueError("total_cases must be at least 2.")

        num_valid = total_cases // 2
        num_invalid = total_cases - num_valid

        test_cases = []
        for _ in range(num_valid):
            test_cases.append({
                "data": self._generate_valid_case(),
                "is_valid": True
            })

        # Ensure we have a pool of valid cases to draw from for invalidation
        valid_pool = [self._generate_valid_case() for _ in range(num_invalid)]

        for i in range(num_invalid):
            test_cases.append({
                "data": self._generate_invalid_case(valid_pool[i]),
                "is_valid": False
            })

        return test_cases

    def _generate_valid_case(self) -> Dict[str, Any]:
        """
        Generates a single dictionary with valid data for the model.
        """
        data = {}
        for name, field in self.fields.items():
            if not field.is_required() and random.choice([True, False]):
                continue
            data[name] = self._generate_value_for_field(field)
        return data

    def _generate_invalid_case(self, base_valid_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a single dictionary with one piece of invalid data,
        starting from a valid case.
        """
        data = base_valid_case.copy()

        field_name_to_invalidate = random.choice(list(self.fields.keys()))
        field_to_invalidate = self.fields[field_name_to_invalidate]

        strategies = [
            self._invalidate_by_type,
            self._invalidate_by_missing_required,
            self._invalidate_by_constraint,
        ]

        strategy = random.choice(strategies)
        invalid_data = strategy(data, field_name_to_invalidate, field_to_invalidate)

        return invalid_data

    def _invalidate_by_type(self, data, name, field):
        """Invalidates by providing a completely wrong type."""
        if field.annotation is int:
            data[name] = "not-an-int"
        elif field.annotation is bool:
            data[name] = "not-a-bool"
        else:
            data[name] = 12345
        return data

    def _invalidate_by_missing_required(self, data, name, field):
        """Invalidates by removing a required field."""
        if field.is_required():
            if name in data:
                del data[name]
        else: # If optional field was picked, invalidate a known required field
            # This makes the invalidation more reliable
            required_fields = [n for n, f in self.fields.items() if f.is_required()]
            if required_fields:
                field_to_remove = random.choice(required_fields)
                if field_to_remove in data:
                    del data[field_to_remove]
        return data

    def _invalidate_by_constraint(self, data, name, field):
        """Invalidates by violating a field's constraint (e.g., max_length)."""
        max_len = next((m.max_length for m in field.metadata if hasattr(m, 'max_length')), None)

        if field.annotation is str and max_len is not None:
            data[name] = ''.join(random.choices(string.ascii_letters, k=max_len + 1))
            return data

        min_items = next((m.min_length for m in field.metadata if hasattr(m, 'min_length')), None) # For lists
        if field.annotation is list and min_items is not None and min_items > 0:
            data[name] = []
            return data

        # Fallback to a different invalidation if no constraint is applicable
        return self._invalidate_by_type(data, name, field)

    def _generate_value_for_field(self, field: FieldInfo) -> Any:
        """
        Generates a valid value for a single field based on its type and constraints.
        """
        field_type = field.annotation

        if field_type is str:
            min_len = next((m.min_length for m in field.metadata if hasattr(m, 'min_length')), None) or 1
            max_len = next((m.max_length for m in field.metadata if hasattr(m, 'max_length')), None) or min_len + 10
            # Ensure min_len is not greater than max_len
            if min_len > max_len:
                min_len = max_len
            length = random.randint(min_len, max_len)
            return ''.join(random.choices(string.ascii_letters, k=length))

        if str(field_type) == '~EmailStr': # Workaround for EmailStr type check
             return "test.user@example.com"

        if field_type is int:
            gt = next((m.gt for m in field.metadata if hasattr(m, 'gt')), None) or 0
            lt = next((m.lt for m in field.metadata if hasattr(m, 'lt')), None) or gt + 100
            return random.randint(gt + 1, lt -1)

        if field_type is bool:
            return random.choice([True, False])

        if field_type is uuid.UUID:
            return uuid.uuid4()

        if field_type is datetime:
            return datetime.utcnow()

        if hasattr(field_type, '__origin__') and field_type.__origin__ is list:
            # This is a simplified list generation
            return ["sample_item"]

        if isinstance(field_type, type) and issubclass(field_type, Enum):
            return random.choice(list(field_type))

        if field_type is dict:
            return {"key": "value"}

        # Fallback for complex types
        try:
            if str(field_type) == '~EmailStr':
                return "test.user@example.com"
            if issubclass(field_type, Enum):
                 return random.choice(list(field_type))
        except TypeError:
            pass

        return None
