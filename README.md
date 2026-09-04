# SignalTrade Portfolio

사용자의 자산과 포지션을 조회하기 위한 서비스입니다. Trading의 거래 기록으로 계산한 전략별 보유 수량과 실제 Upbit 잔고를 비교해 계좌 요약, 손익, 외부 자산과 잔고 불일치 정보를 제공합니다.

## 주요 역할

- 모의·실전 계좌 평가금액과 손익 계산
- 체결 기록을 기준으로 전략별 수량과 평균 매수가 계산
- Upbit 실제 잔고와 SignalTrade 내부 기록 비교
- 전략으로 매수한 자산과 외부에서 보유한 자산 구분
- 실제 수량이 내부 기록보다 부족한 경우 mismatch incident 생성
- 사용자가 부족 수량을 특정 전략에서 차감하는 정합성 조정
- 대시보드와 사용자 분석 화면용 조회 API 제공

Portfolio는 조회와 정합성 관리가 목적이며 거래소 주문은 실행하지 않습니다. 주문과 체결 기록의 원본은 Trading이 계속 소유합니다.

## Write 권한이 있는 테이블

- `position_sync_adjustment`: 어느 전략에서 얼마를 차감했는지 기록
- `position_mismatch_incident`: 실제 잔고와 내부 수량의 불일치 사건
- `message_outbox`: 정합성 조정 결과 이벤트

다음 데이터는 계산에 사용하지만 읽기 전용입니다.

- Trading의 실행·거래·모의 원장
- Strategy의 전략과 사용자 전략 연결 정보
- Identity의 사용자와 API Key 관련 정보

## HTTP 통신

Frontend에 계좌, 잔고, 포지션, 손익과 정합성 API를 제공합니다. 실제 Upbit 잔고가 필요할 때 Identity 내부 HTTP API로 해당 사용자의 거래소 인증 정보를 요청합니다.

Trading의 미완료 실행 복구 과정에서는 Portfolio 내부 API가 계산한 포지션을 제공할 수 있습니다. 서로 필요한 결과는 HTTP로 요청하되 상대 도메인의 테이블을 직접 수정하지 않습니다.

## Queue 통신

사용자가 잔고 부족분을 특정 전략에서 차감하면 `PositionReconciled` 이벤트를 `message_outbox`에 저장합니다. Messaging이 이 이벤트를 Trading Queue로 전송하고 Trading이 자신의 실행 상태에 반영합니다.

Portfolio는 현재 Queue를 직접 소비하지 않으며 Redis도 사용하지 않습니다.
