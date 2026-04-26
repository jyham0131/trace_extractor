# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

장애 발생 시 로그 파일에서 거래 추적번호를 기반으로 관련 로그를 추출·분석하는 **tkinter 데스크탑 UI** 도구. PyInstaller로 exe 빌드 가능.

---

## 로그 포맷

```
[260426 21:56:17.725] [ 프로세스번호 ] [추적번호16자리] 데이터...
```

- 필드 0: 타임스탬프 `[YYMMDD HH:MM:SS.mmm]`
- 필드 1: 프로세스 번호 `[ NNNN ]`
- 필드 2: 추적번호 16자리 `[XXXXXXXXXXXXXXXX]`
- 필드 3~: 페이로드 데이터

### Xlog 파일 특이사항

- 파일명이 `Xlog`로 시작하는 파일은 **필드 1** 위치에 추적번호가 릴레이(relay)된다.
- 다른 파일들은 필드 1이 단순 프로세스 번호이며 추적번호로 사용되지 않는다.

---

## 3단계 분석 흐름

```
1단계 │ 입력 추적번호(들) → 해당 추적번호가 포함된 라인 추출
      ↓
2단계 │ 1단계 결과 + 키워드2 → Xlog 파일 필드1에서 새 추적번호 발견
      ↓
3단계 │ 발견된 추적번호 + 키워드3 → 매칭/미매칭 분리 출력
```

---

## 아키텍처

```
Claude_Pro/
├── app.py               # PyQt6 메인 윈도우 (UI 진입점)
├── log_parser.py        # 로그 라인 파싱 (LogLine 데이터클래스)
├── trace_extractor.py   # 3단계 분석 로직
├── xlog_handler.py      # Xlog 릴레이 추적번호 처리
├── result_reporter.py   # AnalysisResult 데이터 구조
├── requirements.txt     # PyInstaller (tkinter는 Python 표준 라이브러리)
├── build.bat            # exe 빌드 스크립트
└── tests/
    ├── test_log_parser.py
    ├── test_trace_extractor.py
    └── test_result_reporter.py
```

### 핵심 모듈 책임

| 모듈 | 책임 |
|------|------|
| `log_parser.py` | 로그 한 줄 → `LogLine` 변환, 파일 전체 파싱 |
| `xlog_handler.py` | Xlog 필드1에서 릴레이 추적번호 추출 |
| `trace_extractor.py` | step1/2/3 필터링 함수 |
| `result_reporter.py` | `AnalysisResult` 집계 (매칭/미매칭/카운트) |
| `app.py` | tkinter UI — 파일 선택, 키워드 입력, 결과 테이블 |

---

## 개발 환경 및 명령어

```bash
# 의존성 설치
pip install -r requirements.txt

# UI 실행
python app.py

# exe 빌드 (build.bat 또는 직접)
pyinstaller --onefile --windowed --name LogAnalyzer app.py

# 테스트 전체
pytest

# 단일 테스트
pytest tests/test_log_parser.py::test_parse_normal_line -v

# 린트
flake8 . --max-line-length=100
```

---

## 코딩 규칙

- **언어**: Python 3.10+, 타입힌트 필수
- **주석**: 한국어 (WHY 중심)
- **스타일**: 함수 단일 책임, 20줄 이하 권장
- **데이터 모델**: `dataclass` 사용, dict 직접 노출 지양
- **출력 구분**: 매칭 결과와 미매칭 결과는 반드시 분리 표시
