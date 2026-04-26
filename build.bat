@echo off
echo ===== 로그 분석기 EXE 빌드 시작 =====

pyinstaller ^
  --onefile ^
  --windowed ^
  --name LogAnalyzer ^
  --add-data "log_parser.py;." ^
  --add-data "trace_extractor.py;." ^
  --add-data "xlog_handler.py;." ^
  --add-data "result_reporter.py;." ^
  app.py

echo.
echo ===== 빌드 완료 =====
echo dist\LogAnalyzer.exe 를 실행하세요.
pause
