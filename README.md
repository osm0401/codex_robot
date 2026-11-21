# AI 육아 로봇

두 사람이 함께 돌보는 연습용 아기 로봇의 소프트웨어입니다.

## 실행 방법

Python 3.11이 필요합니다. 프로젝트 루트에서 가상환경을 만든 뒤 의존성을 설치합니다.

Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app
```

Linux·macOS

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m app
```

`GET /health`는 HTTP 200과 `{"status":"ok"}`를 반환합니다. 기본 포트는 8000입니다. 다른 포트가 필요하면 `.env.example`을 `.env`로 복사한 뒤 `APP_PORT`를 조정하세요. 같은 이름의 환경변수가 있으면 그 값을 우선합니다. 서버는 항상 `127.0.0.1`에서 실행됩니다.

[아기 화면](http://127.0.0.1:8000/)을 열고 표정과 행동을 살펴보세요. 밥 주기, 트림 돕기, 기저귀 갈기, 재우기, 안아 주기 버튼으로 아기의 상태가 달라집니다. `BABY_SPEED=30`으로 설정하면 30배속 데모 모드가 켜지고 월령 진행의 최소 날짜 조건이 생략됩니다. 일반 모드는 유효한 돌봄과 경과 일수를 모두 반영합니다.

아기 상태는 기본적으로 프로젝트의 `data/app.db`에 저장됩니다. 데모를 따로 저장하려면 `.env`에 `DATA_DIR=data/demo`를 지정한 뒤 서버를 다시 시작하세요. 상대 경로는 프로젝트 루트를 기준으로 합니다.

## 시뮬레이션 자료

월령별 반응과 일과는 [아기 행동 CSV](docs/baby_behavior/README.md)에 기초합니다. [자료 출처](docs/baby_behavior/sources.csv)와 아기 화면 도움말에서 CDC, AAP, WHO 등 원자료를 확인할 수 있습니다. 표시되는 월령과 신호는 가상 아기 시뮬레이션에 사용됩니다.

## 테스트

가상환경의 Python으로 `python -m pytest`를 실행합니다. 웹캠, 마이크, 모델 파일, 외부 네트워크, API 키 없이 실행할 수 있습니다. GitHub Actions는 Linux와 Windows의 Python 3.11에서 같은 테스트를 실행합니다.

## 개인정보 처리

S1까지 서버는 장치를 사용하거나 사람에 관한 데이터를 수집하지 않습니다. SQLite에는 가상 아기의 월령과 욕구 등 상태 한 행만 저장합니다. 개인정보·안전 원칙 15개는 [AGENTS.md](AGENTS.md)에 있습니다.

얼굴 특징값은 별도 얼굴 동의를 한 2명만, Fernet 암호화해 저장. 화면의 다른 얼굴은 비교를 위해 메모리에서 잠깐 특징값을 만들 수 있지만, 비교 직후 즉시 버리고 저장·로그하지 않는다.

## 단계 진행 상황

| 단계 | 상태 |
| --- | --- |
| [S0 기반 구성](docs/stages/S0.md) | 완료 |
| [S1 자라는 아기 AI](docs/stages/S1.md) | 구현 |
| S2~S11 | 단계별 구현 예정 |
