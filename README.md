# SignalTrade Portfolio

전략 포지션, 실제 잔고 정합성, 손익 조회를 맡는 서비스입니다.

```text
src/signaltrade_portfolio/  포지션 API·정합성 Worker
tests/                      포지션·잔고 테스트
```

Trading의 체결 데이터를 읽어 포지션을 계산하며 직접 수정하지 않습니다. 실제 잔고가 부족하면 incident를 기록하고, 사용자가 선택한 차감 결과는 Outbox로 발행합니다.
