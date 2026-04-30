from dataclasses import dataclass, field
from log_parser import LogLine


@dataclass
class AnalysisResult:
    step1_lines: list[LogLine] = field(default_factory=list)
    step2_traces: set[str] = field(default_factory=set)
    step2_mapping: dict[str, str] = field(default_factory=dict)  # 릴레이추적번호 → 원본추적번호
    matched_lines: list[LogLine] = field(default_factory=list)
    unmatched_trace_ids: set[str] = field(default_factory=set)

    @property
    def matched_count(self) -> int:
        return len(self.matched_lines)

    @property
    def unmatched_count(self) -> int:
        return len(self.unmatched_trace_ids)

    @property
    def summary(self) -> str:
        return (
            f"1단계: {len(self.step1_lines)}줄 추출 | "
            f"2단계: {len(self.step2_traces)}개 추적번호 발견 | "
            f"매칭: {self.matched_count}건 | 미매칭: {self.unmatched_count}건"
        )
