<#
==============================================================================
Unified Local System Launcher Script
Hierarchical Highlights Summarizer System

Automatically targets dedicated virtual environments:
  1. ASR-Module (Port 8000)   -> .asr-module-venv\Scripts\python.exe
  2. SD-Module  (Port 8002)   -> .sd-module-venv\Scripts\python.exe
  3. LLMs-Module(Port 8003)   -> .llms-module-venv\Scripts\python.exe
  4. Backend Gateway (8080)   -> .backend-gateway-venv\Scripts\python.exe (PYTHONPATH=.)
  5. Frontend   (Port 8501)   -> npm run dev
==============================================================================
#>

$ErrorActionPreference = "Stop"

$PROJECT_ROOT = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location -Path $PROJECT_ROOT

Write-Host "======================================================================"
Write-Host "LAUNCHING HIERARCHICAL HIGHLIGHTS SUMMARIZER SYSTEM (LOCAL MODE)"
Write-Host "======================================================================"

$Processes = @()

try {
    # 1. Start ASR-Module (Port 8000)
    Write-Host "[1/5] Starting ASR-Module (Sherpa-ONNX) on http://localhost:8000 ..."
    $env:PYTHONPATH = "."
    $asrProc = Start-Process -NoNewWindow -PassThru -FilePath "$PROJECT_ROOT\backend\asr-module\.asr-module-venv\Scripts\python.exe" -ArgumentList "main.py" -WorkingDirectory "$PROJECT_ROOT\backend\asr-module"
    $Processes += $asrProc

    # 2. Start SD-Module (Port 8002)
    Write-Host "[2/5] Starting SD-Module (Diarization) on http://localhost:8002 ..."
    $sdProc = Start-Process -NoNewWindow -PassThru -FilePath "$PROJECT_ROOT\backend\sd-module\.sd-module-venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8002" -WorkingDirectory "$PROJECT_ROOT\backend\sd-module"
    $Processes += $sdProc

    # 3. Start LLMs-Module (Port 8003)
    Write-Host "[3/5] Starting LLMs-Module (ViT5 / BARTpho) on http://localhost:8003 ..."
    $llmProc = Start-Process -NoNewWindow -PassThru -FilePath "$PROJECT_ROOT\backend\llms-module\.llms-module-venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "runtime.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8003" -WorkingDirectory "$PROJECT_ROOT\backend\llms-module"
    $Processes += $llmProc

    # 4. Start Central Backend Gateway (Port 8080)
    Write-Host "[4/5] Starting Central Backend Gateway on http://localhost:8080 ..."
    $gwProc = Start-Process -NoNewWindow -PassThru -FilePath "$PROJECT_ROOT\backend\.backend-gateway-venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "backend.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--reload" -WorkingDirectory "$PROJECT_ROOT"
    $Processes += $gwProc

    # Wait for Backend Gateway (Port 8080) readiness before opening Frontend UI
    Write-Host "Waiting for Backend Gateway (Port 8080) readiness probe..."
    $gatewayReady = $false
    for ($i = 1; $i -le 20; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "Backend Gateway is online and ready!"
                $gatewayReady = $true
                break
            }
        } catch {
            # Ignore errors and wait
        }
        Start-Sleep -Milliseconds 300
    }

    # 5. Start React Frontend UI (Port 8501)
    if (Test-Path "$PROJECT_ROOT\frontend") {
        Write-Host "[5/5] Starting React Frontend Interface on http://localhost:8501 ..."
        $feProc = Start-Process -NoNewWindow -PassThru -FilePath "cmd.exe" -ArgumentList "/c", "npm", "run", "dev", "--", "--port", "8501", "--host" -WorkingDirectory "$PROJECT_ROOT\frontend"
        $Processes += $feProc
    }

    Write-Host "======================================================================"
    Write-Host "ALL SYSTEM SERVICES LAUNCHED AND RUNNING!"
    Write-Host "   - ASR Service:      http://localhost:8000/docs"
    Write-Host "   - SD Service:       http://localhost:8002/docs"
    Write-Host "   - LLM Service:      http://localhost:8003/docs"
    Write-Host "   - Backend Gateway:  http://localhost:8080/docs"
    Write-Host "   - Frontend UI:      http://localhost:8501"
    Write-Host "======================================================================"
    Write-Host "Press Ctrl+C at any time to shutdown all microservices."

    # Keep script active to await processes
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host ""
    Write-Host "======================================================================"
    Write-Host "STOPPING ALL LOCAL MICROSERVICES..."
    Write-Host "======================================================================"
    foreach ($proc in $Processes) {
        if ($null -ne $proc -and -not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "All microservice processes stopped cleanly."
}
