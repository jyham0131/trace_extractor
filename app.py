import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from log_parser import parse_file_content
from trace_extractor import step1_filter, step2_find_new_traces, step3_match
from result_reporter import AnalysisResult
from ulog_parser import parse_file_content as ulog_parse_file
from ulog_extractor import collect_keywords, extract_by_keywords


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("로그 분석기")
        self.minsize(1100, 720)
        self._log_files: dict[str, str] = {}
        self._ulog_files: dict[str, str] = {}
        self._last_result = None
        self._unmatched_all_ids: list[str] = []         # 검색 초기화용 전체 미매칭 목록
        self._unmatched_step2_mapping: dict[str, str] = {}  # 릴레이→원본 추적번호 매핑
        self._kw_config = self._load_keywords()
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

        # slog 파일 행
        row1 = ttk.Frame(frame)
        row1.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(row1, text="📂  slog 파일 선택", command=self._select_files).pack(side="left", padx=(0, 10))
        self._file_var = tk.StringVar(value="선택된 파일 없음")
        ttk.Label(row1, textvariable=self._file_var, foreground="#57606a",
                  font=("맑은 고딕", 9)).pack(side="left", fill="x", expand=True)

        # ulog 파일 행
        row2 = ttk.Frame(frame)
        row2.pack(fill="x", padx=4)
        ttk.Button(row2, text="📂  ulog 파일 선택", command=self._select_ulog_files).pack(side="left", padx=(0, 10))
        self._ulog_file_var = tk.StringVar(value="선택된 파일 없음")
        ttk.Label(row2, textvariable=self._ulog_file_var, foreground="#57606a",
                  font=("맑은 고딕", 9)).pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="📋  ulog 분석",
                   command=self._on_ulog_analysis_click).pack(side="right", padx=(10, 0))

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
        self._kw2_combo = ttk.Combobox(col2, textvariable=self._kw2_var,
                                       values=self._kw_config["step2"])
        self._kw2_combo.pack(fill="x")

        # 3단계 - 키워드
        col3 = ttk.Frame(inner)
        col3.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ttk.Label(col3, text="3단계 · 키워드").pack(anchor="w")
        self._kw3_var = tk.StringVar()
        self._kw3_combo = ttk.Combobox(col3, textvariable=self._kw3_var,
                                       values=self._kw_config["step3"])
        self._kw3_combo.pack(fill="x")

        # 키워드 관리 버튼
        col_mgr = ttk.Frame(inner)
        col_mgr.pack(side="left", padx=(0, 10))
        ttk.Label(col_mgr, text="").pack()
        ttk.Button(col_mgr, text="⚙ 키워드 관리",
                   command=self._open_keyword_manager).pack()

        # 분석 버튼
        col4 = ttk.Frame(inner)
        col4.pack(side="left")
        ttk.Label(col4, text="").pack()   # 라벨과 높이 맞추기
        btn = ttk.Button(col4, text="🔍  slog 분석",
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
            columns=["파일명", "타임스탬프", "프로세스번호", "추적번호", "원본 추적번호", "내용"],
            widths=[130, 150, 110, 160, 160, 500],
        )

        # 미매칭 탭
        tab_unmatched = ttk.Frame(self._notebook)
        self._notebook.add(tab_unmatched, text="  ❌  미매칭  (0건)  ")

        # 미매칭 탭 전용 검색 바 (기존 분석 로직과 완전히 독립)
        search_bar = ttk.Frame(tab_unmatched)
        search_bar.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Label(search_bar, text="검색:").pack(side="left", padx=(0, 4))
        self._unmatched_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_bar, textvariable=self._unmatched_search_var, width=30)
        search_entry.pack(side="left", padx=(0, 4))
        search_entry.bind("<Return>", lambda *_: self._filter_unmatched())
        ttk.Button(search_bar, text="검색", command=self._filter_unmatched).pack(side="left", padx=(0, 4))
        ttk.Button(search_bar, text="초기화", command=self._reset_unmatched_filter).pack(side="left")

        self._unmatched_tree = self._make_tree(
            tab_unmatched,
            columns=["미매칭 추적번호", "원본 추적번호"],
            widths=[300, 300],
        )

        # ulog 매칭 탭
        tab_ulog = ttk.Frame(self._notebook)
        self._notebook.add(tab_ulog, text="  📋  ulog  (0건)  ")
        self._ulog_tree = self._make_tree(
            tab_ulog,
            columns=["파일명", "타임스탬프", "프로세스번호", "추적번호", "원본 추적번호", "내용"],
            widths=[130, 150, 110, 160, 160, 500],
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
            tree.heading(col, text=col, anchor="w",
                         command=lambda c=col, t=tree: self._copy_column(t, c))
            tree.column(col, width=width, anchor="w", minwidth=60, stretch=tk.NO)

        # 짝수 행 배경색 교차
        tree.tag_configure("even", background="#f6f8fa")
        tree.tag_configure("odd",  background="#ffffff")
        tree.tag_configure("red",  foreground="#cf222e")

        # 셀 더블클릭 → 해당 셀 값 클립보드 복사
        tree.bind("<Double-1>", lambda e, t=tree: self._on_cell_double_click(e, t))

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

    def _select_ulog_files(self):
        paths = filedialog.askopenfilenames(title="ulog 파일 선택")
        if not paths:
            return

        self._ulog_files.clear()
        failed = []
        for path in paths:
            try:
                content = self._read_ulog_file(path)
                self._ulog_files[Path(path).name] = content
            except Exception as e:
                failed.append(f"{Path(path).name}: {e}")

        if failed:
            messagebox.showwarning("파일 읽기 오류", "\n".join(failed))

        names = "  |  ".join(self._ulog_files.keys())
        self._ulog_file_var.set(f"{len(self._ulog_files)}개 파일 선택됨  —  {names}")
        self._set_status(f"ulog {len(self._ulog_files)}개 파일 로드 완료.")

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
        step2_mapping = step2_find_new_traces(step1, kw2)
        step2_traces = set(step2_mapping.keys())
        matched, unmatched_ids = step3_match(all_lines, step2_traces, kw3)

        result = AnalysisResult(
            step1_lines=step1,
            step2_traces=step2_traces,
            step2_mapping=step2_mapping,
            matched_lines=matched,
            unmatched_trace_ids=unmatched_ids,
        )
        self._last_result = result
        self._render_result(result)

    # ── 결과 렌더링 ───────────────────────────────────────

    def _render_result(self, result: AnalysisResult):
        # 매칭 테이블
        self._clear_tree(self._matched_tree)
        for i, line in enumerate(result.matched_lines):
            tag = "even" if i % 2 == 0 else "odd"
            origin = result.step2_mapping.get(line.trace_id, "")
            self._matched_tree.insert(
                "", "end",
                values=(line.source_file, line.timestamp, line.field1,
                        line.trace_id, origin, line.payload),
                tags=(tag,)
            )

        # 미매칭 테이블
        self._unmatched_all_ids = sorted(result.unmatched_trace_ids)
        self._unmatched_step2_mapping = result.step2_mapping
        self._unmatched_search_var.set("")
        self._clear_tree(self._unmatched_tree)
        for tid in self._unmatched_all_ids:
            origin = self._unmatched_step2_mapping.get(tid, "")
            self._unmatched_tree.insert("", "end", values=(tid, origin), tags=("red",))

        # 탭 제목 갱신
        self._notebook.tab(0, text=f"  ✅  매칭  ({result.matched_count}건)  ")
        self._notebook.tab(1, text=f"  ❌  미매칭  ({result.unmatched_count}건)  ")

        # 결과 있는 탭으로 이동
        self._notebook.select(0 if result.matched_count > 0 else 1)

        self._set_status(result.summary)

    # ── ulog 분석 ─────────────────────────────────────────

    def _on_ulog_analysis_click(self):
        if self._last_result is None:
            messagebox.showwarning("경고", "먼저 slog 분석을 실행해주세요.")
            return
        self._run_ulog_analysis(self._last_result)

    def _run_ulog_analysis(self, result: AnalysisResult):
        if not self._ulog_files:
            self._clear_tree(self._ulog_tree)
            self._ulog_tree.insert("", "end",
                                   values=("(파일 없음)", "", "", "", "", ""),
                                   tags=("red",))
            self._notebook.tab(2, text="  📋  ulog  (파일 없음)  ")
            return

        ulog_all = []
        for filename, content in self._ulog_files.items():
            ulog_all.extend(ulog_parse_file(content, filename))

        trace_kws, proc_kws = collect_keywords(result)
        matched = extract_by_keywords(ulog_all, trace_kws, proc_kws)

        original_ids = {line.trace_id for line in result.step1_lines}

        self._clear_tree(self._ulog_tree)
        for i, line in enumerate(matched):
            relay = next((tid for tid in result.step2_traces if tid in line.raw), "")
            original = result.step2_mapping.get(relay) or next(
                (tid for tid in original_ids if tid in line.raw), ""
            )
            tag = "even" if i % 2 == 0 else "odd"
            if line.parsed:
                values = (line.source_file, line.datetime, line.process, relay, original, line.content)
            else:
                values = (line.source_file, "", "", relay, original, line.raw)
            self._ulog_tree.insert("", "end", values=values, tags=(tag,))

        if matched:
            max_len = max(
                len(line.content if line.parsed else line.raw) for line in matched
            )
            self._ulog_tree.column("내용", width=max(500, max_len * 7))

        self._notebook.tab(2, text=f"  ✅  ulog  ({len(matched)}건)  ")

    def _on_cell_double_click(self, event: tk.Event, tree: ttk.Treeview):
        """더블클릭한 셀의 값을 클립보드에 복사."""
        if tree.identify_region(event.x, event.y) != "cell":
            return
        row = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not row:
            return
        col_idx = int(col[1:]) - 1
        values = tree.item(row, "values")
        if col_idx < len(values):
            self.clipboard_clear()
            self.clipboard_append(str(values[col_idx]))
            self._set_status(f"복사됨: {values[col_idx]}")

    # ── 열 헤더 클릭 → 해당 열 전체 복사 ────────────────────

    def _copy_column(self, tree: ttk.Treeview, col: str):
        col_idx = list(tree["columns"]).index(col)
        rows = tree.get_children()
        values = [str(tree.item(row, "values")[col_idx]) for row in rows]
        tree.selection_set(rows)
        self.clipboard_clear()
        self.clipboard_append("\n".join(values))
        self._set_status(f"'{col}' 열 {len(values)}개 값 복사됨")

    # ── 미매칭 검색 (기존 분석 로직과 독립) ─────────────────

    def _filter_unmatched(self):
        keyword = self._unmatched_search_var.get().strip().lower()
        self._clear_tree(self._unmatched_tree)
        for tid in self._unmatched_all_ids:
            origin = self._unmatched_step2_mapping.get(tid, "")
            if keyword in tid.lower() or keyword in origin.lower():
                self._unmatched_tree.insert("", "end", values=(tid, origin), tags=("red",))

    def _reset_unmatched_filter(self):
        self._unmatched_search_var.set("")
        self._clear_tree(self._unmatched_tree)
        for tid in self._unmatched_all_ids:
            origin = self._unmatched_step2_mapping.get(tid, "")
            self._unmatched_tree.insert("", "end", values=(tid, origin), tags=("red",))

    # ── 키워드 config 관리 ────────────────────────────────

    @staticmethod
    def _config_path() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent / "keywords_config.json"
        return Path(__file__).parent / "keywords_config.json"

    def _load_keywords(self) -> dict[str, list[str]]:
        default: dict[str, list[str]] = {"step2": [], "step3": []}
        try:
            data = json.loads(self._config_path().read_text(encoding="utf-8"))
            return {"step2": list(data.get("step2", [])),
                    "step3": list(data.get("step3", []))}
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _save_keywords(self):
        self._config_path().write_text(
            json.dumps(self._kw_config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _refresh_comboboxes(self):
        self._kw2_combo["values"] = self._kw_config["step2"]
        self._kw3_combo["values"] = self._kw_config["step3"]

    def _open_keyword_manager(self):
        dlg = tk.Toplevel(self)
        dlg.title("키워드 관리")
        dlg.resizable(True, False)
        dlg.grab_set()

        for step, label in [("step2", "2단계 키워드"), ("step3", "3단계 키워드")]:
            grp = ttk.LabelFrame(dlg, text=f" {label} ")
            grp.pack(fill="both", expand=True, padx=12, pady=(8, 4))

            lb_wrap = ttk.Frame(grp)
            lb_wrap.pack(fill="both", expand=True)
            lb = tk.Listbox(lb_wrap, selectmode="single", height=7, width=42,
                            font=("맑은 고딕", 10))
            vsb = ttk.Scrollbar(lb_wrap, orient="vertical", command=lb.yview)
            lb.configure(yscrollcommand=vsb.set)
            vsb.pack(side="right", fill="y")
            lb.pack(side="left", fill="both", expand=True)

            for kw in self._kw_config[step]:
                lb.insert("end", kw)

            entry_var = tk.StringVar()

            def on_select(_, lbx=lb, ev=entry_var):
                sel = lbx.curselection()
                if sel:
                    ev.set(lbx.get(sel[0]))

            lb.bind("<<ListboxSelect>>", on_select)

            btn_row = ttk.Frame(grp)
            btn_row.pack(fill="x", pady=(6, 4))

            entry = ttk.Entry(btn_row, textvariable=entry_var, width=26)
            entry.pack(side="left", padx=(0, 6))

            def do_add(s=step, lbx=lb, ev=entry_var):
                kw = ev.get().strip()
                if not kw or kw in self._kw_config[s]:
                    return
                self._kw_config[s].append(kw)
                lbx.insert("end", kw)
                ev.set("")
                self._save_keywords()
                self._refresh_comboboxes()

            def do_edit(s=step, lbx=lb, ev=entry_var):
                sel = lbx.curselection()
                kw = ev.get().strip()
                if not sel or not kw:
                    return
                idx = sel[0]
                self._kw_config[s][idx] = kw
                lbx.delete(idx)
                lbx.insert(idx, kw)
                lbx.selection_set(idx)
                self._save_keywords()
                self._refresh_comboboxes()

            def do_del(s=step, lbx=lb, ev=entry_var):
                sel = lbx.curselection()
                if not sel:
                    return
                idx = sel[0]
                self._kw_config[s].pop(idx)
                lbx.delete(idx)
                ev.set("")
                self._save_keywords()
                self._refresh_comboboxes()

            entry.bind("<Return>", lambda *_, f=do_add: f())
            ttk.Button(btn_row, text="추가", command=do_add).pack(side="left", padx=(0, 4))
            ttk.Button(btn_row, text="수정", command=do_edit).pack(side="left", padx=(0, 4))
            ttk.Button(btn_row, text="삭제", command=do_del).pack(side="left")

        ttk.Button(dlg, text="닫기", command=dlg.destroy).pack(pady=8)

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
        return Path(path).read_text(encoding="euc-kr", errors="replace")

    @staticmethod
    def _read_ulog_file(path: str) -> str:
        """UTF-8 실패 시 EUC-KR로 재시도. 최종 폴백도 EUC-KR."""
        for enc in ("utf-8", "euc-kr", "cp949"):
            try:
                return Path(path).read_text(encoding=enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return Path(path).read_text(encoding="euc-kr", errors="replace")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
