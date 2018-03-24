import json
from typing import Optional, Union

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # pylint: disable=invalid-name


def json_to_str(data: dict) -> Optional[str]:
    if data is None:
        return None

    if isinstance(data, dict):
        return json.dumps(data)

    return str(data)


def str_to_json(data: str) -> Union[dict, str, None]:
    if data is None:
        return None

    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return data
