import json

from signaltrade_portfolio import upbit_accounts


def test_get_accounts_uses_signed_private_account_request(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return json.dumps([{"currency": "KRW", "balance": "1", "locked": "0"}]).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(upbit_accounts, "urlopen", fake_urlopen)
    rows = upbit_accounts.get_accounts(access_key="access", secret_key="secret",
                                       base_url="https://api.upbit.com", timeout=3)
    assert captured["url"] == "https://api.upbit.com/v1/accounts"
    assert captured["authorization"].startswith("Bearer ")
    assert captured["timeout"] == 3
    assert rows[0]["currency"] == "KRW"
