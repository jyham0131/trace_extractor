from log_parser import LogLine
from xlog_handler import extract_relay_trace_id


def step1_filter(all_lines: list[LogLine], trace_ids: list[str]) -> list[LogLine]:
    """입력된 추적번호 중 하나라도 일치하는 라인만 반환."""
    trace_set = set(trace_ids)
    return [line for line in all_lines if line.trace_id in trace_set]


def step2_find_new_traces(step1_lines: list[LogLine], keyword: str) -> set[str]:
    """1단계 결과에서 keyword를 포함하는 Xlog 라인의 릴레이 추적번호를 수집.
    keyword가 비어있으면 모든 Xlog 라인에서 수집."""
    new_traces: set[str] = set()
    for line in step1_lines:
        if keyword and keyword not in line.raw:
            continue
        relay = extract_relay_trace_id(line)
        if relay:
            new_traces.add(relay)
    return new_traces


def step3_match(
    all_lines: list[LogLine],
    trace_ids: set[str],
    keyword: str,
) -> tuple[list[LogLine], set[str]]:
    """2단계 추적번호 중 keyword를 만족하는 라인(매칭)과 미매칭 추적번호를 분리."""
    matched_lines: list[LogLine] = []
    matched_ids: set[str] = set()

    for line in all_lines:
        if line.trace_id not in trace_ids:
            continue
        if keyword and keyword not in line.raw:
            continue
        matched_lines.append(line)
        matched_ids.add(line.trace_id)

    unmatched_ids = trace_ids - matched_ids
    return matched_lines, unmatched_ids
