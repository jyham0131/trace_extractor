import re
from log_parser import LogLine

# Xlog 필드1의 릴레이 추적번호는 16자리 영숫자
_TRACE_ID_PATTERN = re.compile(r'^[A-Za-z0-9]{16}$')


def extract_relay_trace_id(line: LogLine) -> 'str | None':
    """Xlog 파일에서만 field1이 릴레이 추적번호 역할을 하므로, 해당 값을 반환.
    일반 파일이거나 field1이 추적번호 형식이 아니면 None 반환."""
    if not line.is_xlog:
        return None
    if _TRACE_ID_PATTERN.match(line.field1):
        return line.field1
    return None
