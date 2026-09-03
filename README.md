# SignalTrade Portfolio

전략이 보유한 포지션과 실제 Upbit 잔고를 비교하고, 계좌 요약·손익·정합성 정보를 제공하는 서비스입니다. 주문을 실행하지 않으며 Trading 기록을 읽어 조회 모델을 만듭니다.

## 주요 책임

- 전략별 보유 수량과 평균 매수가 계산
- 실제 계좌 잔고와 전략 기록의 정합성 비교
- 외부 자산, 전략 귀속 자산, 부족 수량 분리
- 실전·모의 계좌 요약과 손익 API 제공
- 부족 수량 incident와 사용자 선택 차감 원장 기록

## 디렉터리

```text
src/signaltrade_portfolio/
  api_reporting.py       계좌·포지션·분석 API
  api_reconciliation.py  정합성 조회·차감 API
  worker.py              주기적 잔고 점검 Worker
  positions.py           체결 기록 기반 포지션 계산
  reconciliation.py      실제 잔고와 전략 수량 비교
tests/                   포지션, incident, 차감, API 테스트
```

## 다른 서비스와 통신

Frontend는 `/positions`, `/analytics` API로 실전계좌·모의계좌 화면을 구성합니다. Worker는 Upbit 잔고를 읽고 Trading의 체결 기록과 비교합니다.

부족분을 사용자가 특정 전략에서 차감하면 `PositionReconciled` 이벤트를 Outbox에 기록합니다. Messaging이 이를 Queue로 발행해 관련 서비스가 반영할 수 있습니다.

## 로컬 확인

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
```

API와 정합성 Worker는 kind에서 별도 Pod로 실행됩니다.
