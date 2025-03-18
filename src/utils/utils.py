# utils/utils.py
from typing import Any, Dict, List


class Utils:
    @staticmethod
    def escape_special_chars(message: str) -> str:
        return message.replace("{", "[CURLY_OPEN]").replace("}", "[CURLY_CLOSE]")

    @staticmethod
    def get_nested_value(data: Dict, keys: List[str], default: Any = None) -> Any:
        """
        Safely retrieves a nested value from a dictionary using a list of keys.

        Args:
            data: The dictionary to retrieve the value from
            keys: A list of keys representing the path to the nested value
            default: The value to return if the path doesn't exist

        Returns:
            The value at the specified path or the default value if the path doesn't exist
        """
        current = data
        for key in keys:
            if not current or not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current
