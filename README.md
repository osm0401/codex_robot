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

## 테스트

가상환경의 Python으로 `python -m pytest`를 실행합니다. 웹캠, 마이크, 모델 파일, 외부 네트워크, API 키 없이 실행할 수 있습니다. GitHub Actions는 Linux와 Windows의 Python 3.11에서 같은 테스트를 실행합니다.

## 개인정보 처리

S0 서버는 장치를 사용하거나 사람에 관한 데이터를 수집하지 않습니다. 이후 단계에서 적용할 개인정보·안전 원칙 15개는 [AGENTS.md](AGENTS.md)에 있습니다.

얼굴 특징값은 별도 얼굴 동의를 한 2명만, Fernet 암호화해 저장. 화면의 다른 얼굴은 비교를 위해 메모리에서 잠깐 특징값을 만들 수 있지만, 비교 직후 즉시 버리고 저장·로그하지 않는다.

## 단계 진행 상황

| 단계 | 상태 |
| --- | --- |
| [S0 기반 구성](docs/stages/S0.md) | 구현 및 클라우드 검증 |
| S1~S11 | 단계별 구현 예정 |
