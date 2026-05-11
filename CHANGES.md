# 변경사항

기준 커밋: `6a784a7` (미매칭 탭 검색·원본추적번호 열 추가, 열 헤더 복사, 키워드 config 관리 기능)

---

## 신규 파일

### `ulog_parser.py`
- `UlogLine` 데이터클래스 추가 (`raw`, `source_file`, `datetime`, `process`, `content`, `parsed`)
- 정규식으로 `[datetime] [process] 나머지` 구조 파싱
- 파싱 실패 라인도 `raw` 보존 (egrep 매칭은 raw 기준이므로 None 반환 없음)

### `ulog_extractor.py`
- `collect_keywords(result)` — slog 분석 결과에서 검색어 수집
  - 원본 추적번호 (`step1_lines[].trace_id`)
  - 릴레이 추적번호 (`step2_traces`)
  - 프로세스번호 (`step1_lines[].field1`)
  - 반환 타입: `tuple[set[str], set[str]]` — (추적번호 키워드, 프로세스번호 키워드) 분리
- `extract_by_keywords(lines, trace_keywords, proc_keywords)` — egrep 방식 매칭
  - 추적번호: OR 조건 (하나라도 raw에 포함)
  - 프로세스번호: AND 조건 (추적번호 매칭 후 추가 필터)

---

## `app.py` 수정사항

### 파일 선택 UI 분리
- 기존 단일 "파일 선택" → slog / ulog 파일 선택 버튼 행 분리
- ulog 행 우측에 "📋 ulog 분석" 버튼 추가

### 분석 버튼 분리
- "분석 시작" → "🔍 slog 분석" (slog만 실행)
- "📋 ulog 분석" (별도 버튼) — slog 분석 결과 저장 후 ulog 독립 실행
- `self._last_result` 에 slog 결과 저장, ulog 분석 시 재사용
- slog 분석 전 ulog 분석 시도 시 경고 메시지 표시

### ulog 결과 탭 추가 (탭 index 2)
- 컬럼: `파일명 / 타임스탬프 / 프로세스번호 / 추적번호 / 원본 추적번호 / 내용`
  - slog 매칭 탭과 동일한 컬럼 구조
- 추적번호: ulog raw에서 step2 릴레이 추적번호 검색
- 원본 추적번호: step2_mapping 조회, 없으면 원본 추적번호 직접 표시
- ulog 파일 미선택 시: `(파일 없음)` 빨간색 표시, slog 탭 정상 동작

### 좌우 스크롤 수정
- `_make_tree` 컬럼에 `stretch=tk.NO` 추가
- 컬럼 합계 너비가 화면을 초과하면 좌우 스크롤 활성화

### ulog 파일 인코딩 수정
- `_read_ulog_file` 메서드 신규 추가
- ulog 전용 인코딩 순서: `CP949 → EUC-KR → UTF-8`
  - 기존 `_read_file` (UTF-8 우선)로 읽으면 한글·특수문자(`①` 등) 깨지는 문제 해결
- slog는 기존 `_read_file` (UTF-8 우선) 유지
