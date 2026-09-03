import base64
import hashlib
import hmac
import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class UpbitAccountError(RuntimeError):
    pass


def get_accounts(*, access_key: str, secret_key: str, base_url: str,
                 timeout: float = 5.0) -> list[dict]:
    request = Request(
        f"{base_url.rstrip('/')}/v1/accounts",
        headers={"Accept": "application/json",
                 "Authorization": f"Bearer {_create_jwt(access_key, secret_key)}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        message = {
            401: "Upbit Access Key 또는 Secret Key가 올바르지 않습니다.",
            403: "Upbit API Key 권한 또는 허용 IP 설정을 확인해 주세요.",
            429: "Upbit API 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.",
        }.get(error.code, "Upbit API Key 검증에 실패했습니다.")
        raise UpbitAccountError(message) from error
    except URLError as error:
        raise UpbitAccountError("Upbit API 서버에 연결할 수 없습니다.") from error
    except TimeoutError as error:
        raise UpbitAccountError("Upbit API 서버 응답 시간이 초과되었습니다.") from error
    if not isinstance(result, list):
        raise UpbitAccountError("Upbit 계좌 응답 형식이 올바르지 않습니다.")
    return result


def _create_jwt(access_key: str, secret_key: str) -> str:
    header = _base64url_json({"alg": "HS512", "typ": "JWT"})
    payload = _base64url_json({"access_key": access_key, "nonce": str(uuid.uuid4())})
    signing_input = f"{header}.{payload}"
    signature = hmac.new(secret_key.encode(), signing_input.encode("ascii"),
                         hashlib.sha512).digest()
    return f"{signing_input}.{_base64url(signature)}"


def _base64url_json(value: dict[str, str]) -> str:
    return _base64url(json.dumps(value, separators=(",", ":"),
                                 ensure_ascii=False).encode())


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
