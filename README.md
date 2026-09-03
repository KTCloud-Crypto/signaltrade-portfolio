# signaltrade-portfolio

SignalTrade의 전략 포지션 투영, 거래소 잔고 reconciliation 및 포지션 조정 원장을
소유하는 독립 서비스입니다. 주문 실행 원장은 Trading에서 읽기만 하며 변경하지
않습니다.

- `portfolio-worker`: 실제 잔고 shortfall을 감시하고 incident lifecycle을 기록합니다.
- `GET /positions/reconciliation`: 사용자별 실제 잔고와 전략 포지션 차이를 조회합니다.
- `POST /positions/reconciliation/deduct`: 사용자가 선택한 전략에서 부족 수량을 차감하고
  같은 DB 트랜잭션에 `PositionReconciled` Outbox를 기록합니다.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
```

기준 코드는 `KTCloud-Crypto`의 `feat/132`, 커밋
`013107ae8ddd08bed02d88db89af7eeb0cf65bba`입니다.
