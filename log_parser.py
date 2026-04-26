import re
import os
from dataclasses import dataclass

# 로그 라인 정규식: [타임스탬프] [필드1] [16자리추적번호] 페이로드
_LOG_PATTERN = re.compile(
    r'\[(\d{6} \d{2}:\d{2}:\d{2}\.\d{3})\]\s*\[(.+?)\]\s*\[([A-Za-z0-9]{16})\](.*)'
)


@dataclass
class LogLine:
    raw: str
    timestamp: str
    field1: str       # 프로세스번호 또는 Xlog의 릴레이 추적번호
    trace_id: str     # 필드2: 16자리 추적번호
    payload: str
    source_file: str
    is_xlog: bool     # 파일명이 Xlog로 시작하면 True


def parse_line(raw: str, source_file: str) -> 'LogLine | None':
    match = _LOG_PATTERN.match(raw.strip())
    if not match:
        return None

    filename = os.path.basename(source_file)
    # 파일명 대소문자 무관하게 Xlog 식별
    is_xlog = filename.lower().startswith('xlog')

    return LogLine(
        raw=raw.strip(),
        timestamp=match.group(1),
        field1=match.group(2).strip(),
        trace_id=match.group(3),
        payload=match.group(4).strip(),
        source_file=filename,
        is_xlog=is_xlog,
    )


def parse_file_content(content: str, source_file: str) -> list[LogLine]:
    """파일 전체 텍스트를 LogLine 리스트로 변환. 파싱 실패 라인은 무시."""
    lines = []
    for raw in content.splitlines():
        line = parse_line(raw, source_file)
        if line:
            lines.append(line)
    return lines
