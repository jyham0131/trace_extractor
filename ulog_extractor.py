from ulog_parser import UlogLine
from result_reporter import AnalysisResult


def collect_keywords(result: AnalysisResult) -> tuple[set[str], set[str]]:
    """(추적번호 키워드, 프로세스번호 키워드) 분리 반환.
    추적번호는 OR, 프로세스번호는 AND 조건으로 사용."""
    trace_kws = {line.trace_id for line in result.step1_lines if line.trace_id}
    trace_kws.update(result.step2_traces)
    proc_kws = {line.field1 for line in result.step1_lines if line.field1}
    return trace_kws, proc_kws


def extract_by_keywords(
    lines: list[UlogLine],
    trace_keywords: set[str],
    proc_keywords: set[str],
) -> list[UlogLine]:
    """추적번호(OR) AND 프로세스번호(OR) 조건 매칭."""
    if not trace_keywords:
        return []
    return [
        line for line in lines
        if any(kw in line.raw for kw in trace_keywords)
        and (not proc_keywords or any(kw in line.raw for kw in proc_keywords))
    ]
