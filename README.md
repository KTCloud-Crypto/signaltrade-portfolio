# signaltrade-portfolio

SignalTrade의 전략 포지션 투영, 거래소 잔고 reconciliation 및 포지션 조정 원장을
소유하는 독립 서비스입니다. 주문 실행 원장은 Trading에서 읽기만 하며 변경하지
않습니다.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
```

기준 코드는 `KTCloud-Crypto`의 `feat/132`, 커밋
`013107ae8ddd08bed02d88db89af7eeb0cf65bba`입니다.
