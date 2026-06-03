@echo off
setlocal

set "ROOT=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = '%ROOT%';" ^
  "$backend = Join-Path $root 'backend';" ^
  "$frontend = Join-Path $root 'frontend';" ^
  "$procs = @();" ^
  "function Stop-AllChildren { param([array]$items) foreach ($p in $items) { if ($null -ne $p -and -not $p.HasExited) { cmd /c taskkill /PID $p.Id /T /F > $null 2>&1 } } }" ^
  "$handler = [ConsoleCancelEventHandler]{ param($sender, $e) $e.Cancel = $true; Write-Host ''; Write-Host '[dev] Ctrl+C detected, stopping all child processes...'; Stop-AllChildren -items $script:procs; exit 0 };" ^
  "[Console]::add_CancelKeyPress($handler);" ^
  "try {" ^
  "  $procs += Start-Process python -ArgumentList '-m', 'uvicorn', 'app.main:app', '--reload', '--app-dir', '.' -WorkingDirectory $backend -PassThru -NoNewWindow;" ^
  "  $procs += Start-Process python -ArgumentList '-m', 'app.worker' -WorkingDirectory $backend -PassThru -NoNewWindow;" ^
  "  $procs += Start-Process npm.cmd -ArgumentList 'run', 'dev' -WorkingDirectory $frontend -PassThru -NoNewWindow;" ^
  "  $script:procs = $procs;" ^
  "  Write-Host '[dev] Started 3 child processes. Press Ctrl+C to stop all.';" ^
  "  while ($true) { Start-Sleep -Seconds 1; $exited = $procs | Where-Object { $_.HasExited }; if ($exited) { Write-Host '[dev] A child process exited, stopping all...'; Stop-AllChildren -items $procs; exit 1 } }" ^
  "} finally {" ^
  "  [Console]::remove_CancelKeyPress($handler);" ^
  "}"
