import re
from typing import Any

SECRET_KEYS = frozenset({"password", "passwd", "secret", "token", "api_key", "apikey"})
MASK = "****"
_URL_CREDENTIALS = re.compile(r"(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*://)(?P<user>[^:@/\s]*):(?P<password>[^@/\s]+)@")


def mask_url(url: str) -> str:
    return _URL_CREDENTIALS.sub(lambda m: f"{m['scheme']}{m['user']}:{MASK}@", url)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (MASK if isinstance(k, str) and k.lower() in SECRET_KEYS and v else redact(v)) for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return mask_url(value)
    return value
