# 아기 행동 데이터 (0~12개월)

자라는 아기 AI(S1~)의 욕구·신호·하루 리듬 근거 자료. 원본은 엑셀 `아기_행동_목록_0-12개월.xlsx`(2026-11-21)이고, 시트별로 UTF-8 CSV로 옮겼다.

| 파일 | 내용 |
| --- | --- |
| behaviors.csv | 행동 196개 (ID, 분야, 월령, 원인, 부모가 할 일, AI 매핑) |
| ai_mapping.csv | 아기 AI 내부 변수 정의와 관련 행동 ID |
| daily_routine.csv | 월령대별 수유·수면·기저귀 기본값 |
| cry_causes.csv | 울음 원인별 단서와 해결 행동 |
| monthly_summary.csv | 월령별 발달 요약 |
| emergency_signs.csv | 병원·119 안내용 (시뮬레이션에 쓰지 않음) |
| sources.csv | 출처 (CDC, AAP, WHO 등) |

사용 규칙은 프롬프트 v2의 3.1-b절을 따른다. 의료 진단에 쓰지 않는다.
