import re
from log_parser import LogLine

# Xlog payload의 릴레이 추적번호: "TRACE_NO : ABCD1234EFGH5678" 형식
_RELAY_PATTERN = re.compile(r'TRACE_NO\s*:\s*([A-Za-z0-9]{16})')


def extract_relay_trace_id(line: LogLine) -> 'str | None':
    """Xlog 파일의 payload에서 'TRACE_NO : XXXX' 형식의 릴레이 추적번호를 추출.
    Xlog 파일이 아니거나 패턴이 없으면 None 반환."""
    if not line.is_xlog:
        return None
    match = _RELAY_PATTERN.search(line.payload)
    return match.group(1) if match else None
