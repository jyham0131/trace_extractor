import re
import os
from dataclasses import dataclass

_LOG_PATTERN = re.compile(
    r'^\[(?P<datetime>[^\]]+)\]\s+'
    r'\[(?P<process>[^\]]+)\]\s+'
    r'(?P<content>.*)'
)


@dataclass
class UlogLine:
    raw: str
    source_file: str
    datetime: str = ""
    process: str = ""
    content: str = ""
    parsed: bool = False


def parse_line(raw: str, source_file: str) -> UlogLine:
    stripped = raw.strip()
    fname = os.path.basename(source_file)
    match = _LOG_PATTERN.match(stripped)
    if not match:
        return UlogLine(raw=stripped, source_file=fname)
    return UlogLine(
        raw=stripped,
        source_file=fname,
        datetime=match.group('datetime').strip(),
        process=match.group('process').strip(),
        content=match.group('content').strip(),
        parsed=True,
    )


def parse_file_content(content: str, source_file: str) -> list[UlogLine]:
    return [parse_line(raw, source_file) for raw in content.split('\n') if raw.strip()]
