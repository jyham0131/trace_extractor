import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from log_parser import parse_file_content
from trace_extractor import step1_filter, step2_find_new_traces, step3_match
from result_reporter import AnalysisResult


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("로그 분석기")
        self.minsize(1100, 720)
        self._log_files: dict[str, str] = {}
        self._apply_style()
        self._build_ui()

    # ── 스타일 설정 ───────────────────────────────────────

    def _apply_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        bg = "#f4f6f9"
        white = "#ffffff"
        border = "#d0d7de"
        blue = "#0969da"
        header_bg = "#f6f8fa"
        muted = "#57606a"

        self.configure(bg=bg)

        style.configure(".", background=bg, foreground="#24292f",
                        font=("맑은 고딕", 10))
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg)
        style.configure("TLabelframe", background=white, bordercolor=border,
                        relief="solid", padding=8)
        style.configure("TLabelframe.Label", background=white,
                        foreground="#24292f", font=("맑은 고딕", 10, "bold"))
        style.configure("Primary.TButton", background=blue, foreground=white,
                        font=("맑은 고딕", 10, "bold"), relief="flat", padding=(12, 6))
        style.map("Primary.TButton",
                  background=[("active", "#0860ca"), ("pressed", "#0550ae")])
        style.configure("TButton", background=header_bg, foreground="#24292f",
                        relief="solid", bordercolor=border, padding=(10, 5))
        style.map("TButton", background=[("active", "#eaeef2")])
        style.configure("TEntry", fieldbackground=white, bordercolor=border,
                        relief="solid", padding=5)
        style.configure("TNotebook", background=bg, tabmargins=[0, 2, 0, 0])
        style.configure("TNotebook.Tab", background=header_bg, foreground=muted,
                        padding=(16, 6), font=("맑은 고딕", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", white)],
                  foreground=[("selected", blue)],
                  font=[("selected", ("맑은 고딕", 10, "bold"))])
        style.configure("Treeview", background=white, fieldbackground=white,
                        rowheight=24, bordercolor=border, relief="solid",
                        font=("맑은 고딕", 10))
        style.configure("Treeview.Heading", background=header_bg,
                        foreground=muted, font=("맑은 고딕", 10, "bold"),
                        relief="flat", padding=5)
        style.map("Treeview", background=[("selected", "#dbeafe")])
        style.configure("Status.TLabel", background=header_bg,
                        foreground=muted, font=("맑은 고딕", 9), padding=(8, 4))

    # ── UI 구성 ───────────────────────────────────────────

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        self._build_file_section(root)
        self._build_condition_section(root)
        self._build_result_section(root)
        self._build_statusbar()

    def _build_file_section(self, parent):
        frame = ttk.LabelFrame(parent, text=" 로그 파일 ")
        frame.pack(fill="x", pady=(0, 8))

        inner = ttk.Frame(frame)
        inner.pack(fill="x", padx=4)

        btn = ttk.Button(inner, text="📂  파일 선택", command=self._select_files)
        btn.pack(side="left", padx=(0, 10))

        self._file_var = tk.StringVar(value="선택된 파일 없음")
        lbl = ttk.Label(inner, textvariable=self._file_var, foreground="#57606a",
                        font=("맑은 고딕", 9))
        lbl.pack(side="left", fill="x", expand=True)

    def _build_condition_section(self, parent):
        frame = ttk.LabelFrame(parent, text=" 분석 조건 ")
        frame.pack(fill="x", pady=(0, 8))

        inner = ttk.Frame(frame)
        inner.pack(fill="x", padx=4)

        # 1단계 - 추적번호 (여러 줄)
        col1 = ttk.Frame(inner)
        col1.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ttk.Label(col1, text="1단계 · 추적번호 (줄바꿈으로 구분)").pack(anchor="w")
        self._trace_text = tk.Text(col1, height=4, width=28,
                                   font=("맑은 고딕", 10),
                                   relief="solid", bd=1,
                                   bg="#ffffff", fg="#24292f",
                                   insertbackground="#24292f")
        self._trace_text.pack(fill="x")
        self._trace_text.insert("1.0", "")

        # 2단계 - 키워드
        col2 = ttk.Frame(inner)
        col2.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ttk.Label(col2, text="2단계 · 키워드").pack(anchor="w")
        self._kw2_var = tk.StringVar()
        ttk.Entry(col2, textvariable=self._kw2_var).pack(fill="x")

        # 3단계 - 키워드
        col3 = ttk.Frame(inner)
        col3.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ttk.Label(col3, text="3단계 · 키워드").pack(anchor="w")
        self._kw3_var = tk.StringVar()
        ttk.Entry(col3, textvariable=self._kw3_var).pack(fill="x")

        # 분석 버튼
        col4 = ttk.Frame(inner)
        col4.pack(side="left")
        ttk.Label(col4, text="").pack()   # 라벨과 높이 맞추기
        btn = ttk.Button(col4, text="🔍  분석 시작",
                         style="Primary.TButton",
                         command=self._run_analysis)
        btn.pack(ipadx=4, ipady=2)

    def _build_result_section(self, parent):
        self._notebook = ttk.Notebook(parent)
        self._notebook.pack(fill="both", expand=True)

        # 매칭 탭
        tab_matched = ttk.Frame(self._notebook)
        self._notebook.add(tab_matched, text="  ✅  매칭  (0건)  ")
        self._matched_tree = self._make_tree(
            tab_matched,
            columns=["파일명", "타임스탬프", "추적번호", "내용"],
            widths=[130, 150, 160, 500],
        )

        # 미매칭 탭
        tab_unmatched = ttk.Frame(self._notebook)
        self._notebook.add(tab_unmatched, text="  ❌  미매칭  (0건)  ")
        self._unmatched_tree = self._make_tree(
            tab_unmatched,
            columns=["미매칭 추적번호"],
            widths=[300],
        )

    def _make_tree(self, parent, columns: list[str], widths: list[int]) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame, columns=columns, show="headings",
                            selectmode="extended")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)

        for col, width in zip(columns, widths):
            tree.heading(col, text=col, anchor="w")
            tree.column(col, width=width, anchor="w", minwidth=60)

        # 짝수 행 배경색 교차
        tree.tag_configure("even", background="#f6f8fa")
        tree.tag_configure("odd",  background="#ffffff")
        tree.tag_configure("red",  foreground="#cf222e")

        return tree

    def _build_statusbar(self):
        self._status_var = tk.StringVar(value="로그 파일을 선택하고 분석 조건을 입력하세요.")
        bar = ttk.Label(self, textvariable=self._status_var,
                        style="Status.TLabel", anchor="w")
        bar.pack(side="bottom", fill="x")

    # ── 이벤트 핸들러 ─────────────────────────────────────

    def _select_files(self):
        paths = filedialog.askopenfilenames(title="로그 파일 선택")
        if not paths:
            return

        self._log_files.clear()
        failed = []
        for path in paths:
            try:
                content = self._read_file(path)
                self._log_files[Path(path).name] = content
            except Exception as e:
                failed.append(f"{Path(path).name}: {e}")

        if failed:
            messagebox.showwarning("파일 읽기 오류", "\n".join(failed))

        names = "  |  ".join(self._log_files.keys())
        self._file_var.set(f"{len(self._log_files)}개 파일 선택됨  —  {names}")
        self._set_status(f"{len(self._log_files)}개 파일 로드 완료.")

    def _run_analysis(self):
        if not self._log_files:
            messagebox.showwarning("경고", "로그 파일을 먼저 선택해주세요.")
            return

        trace_ids = [
            t.strip()
            for t in self._trace_text.get("1.0", "end").splitlines()
            if t.strip()
        ]
        if not trace_ids:
            messagebox.showwarning("경고", "1단계 추적번호를 입력해주세요.")
            return

        kw2 = self._kw2_var.get().strip()
        kw3 = self._kw3_var.get().strip()

        # 전체 로그 파싱
        all_lines = []
        for filename, content in self._log_files.items():
            all_lines.extend(parse_file_content(content, filename))

        # 3단계 분석
        step1 = step1_filter(all_lines, trace_ids)
        step2_traces = step2_find_new_traces(step1, kw2)
        matched, unmatched_ids = step3_match(all_lines, step2_traces, kw3)

        result = AnalysisResult(
            step1_lines=step1,
            step2_traces=step2_traces,
            matched_lines=matched,
            unmatched_trace_ids=unmatched_ids,
        )
        self._render_result(result)

    # ── 결과 렌더링 ───────────────────────────────────────

    def _render_result(self, result: AnalysisResult):
        # 매칭 테이블
        self._clear_tree(self._matched_tree)
        for i, line in enumerate(result.matched_lines):
            tag = "even" if i % 2 == 0 else "odd"
            self._matched_tree.insert(
                "", "end",
                values=(line.source_file, line.timestamp, line.trace_id, line.payload),
                tags=(tag,)
            )

        # 미매칭 테이블
        self._clear_tree(self._unmatched_tree)
        for i, tid in enumerate(sorted(result.unmatched_trace_ids)):
            self._unmatched_tree.insert("", "end", values=(tid,), tags=("red",))

        # 탭 제목 갱신
        self._notebook.tab(0, text=f"  ✅  매칭  ({result.matched_count}건)  ")
        self._notebook.tab(1, text=f"  ❌  미매칭  ({result.unmatched_count}건)  ")

        # 결과 있는 탭으로 이동
        self._notebook.select(0 if result.matched_count > 0 else 1)

        self._set_status(result.summary)

    # ── 유틸 ─────────────────────────────────────────────

    @staticmethod
    def _clear_tree(tree: ttk.Treeview):
        tree.delete(*tree.get_children())

    def _set_status(self, msg: str):
        self._status_var.set(msg)

    @staticmethod
    def _read_file(path: str) -> str:
        """UTF-8 실패 시 EUC-KR로 재시도. 한국어 로그 파일 대응."""
        for enc in ("utf-8", "euc-kr", "cp949"):
            try:
                return Path(path).read_text(encoding=enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return Path(path).read_text(encoding="utf-8", errors="replace")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
