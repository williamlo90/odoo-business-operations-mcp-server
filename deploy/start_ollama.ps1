param([string]$RuntimePath = "local/ollama-portable/ollama.exe")
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
$runtime = (Resolve-Path -LiteralPath (Join-Path $projectRoot $RuntimePath)).Path
$artifact = Get-Content -Raw -LiteralPath (Join-Path $projectRoot "docs/evidence/phase6-local-runtime.json") | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $runtime -Algorithm SHA256).Hash -ne $artifact.files.'ollama.exe') {
    throw "Ollama executable differs from the validated checkpoint; verify its version and provenance."
}
if (Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue) {
    throw "Port 11434 is already in use; inspect its owner before starting another runtime."
}
$state = Join-Path $projectRoot "local/ollama-runtime"
New-Item -ItemType Directory -Path $state -Force | Out-Null
$env:OLLAMA_HOST = "127.0.0.1:11434"
$env:OLLAMA_NO_CLOUD = "1"
$env:OLLAMA_VULKAN = "0"
$env:GGML_VK_VISIBLE_DEVICES = "-1"
$env:CUDA_VISIBLE_DEVICES = "-1"
$env:OLLAMA_NUM_PARALLEL = "1"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:OLLAMA_MAX_QUEUE = "2"
$env:OLLAMA_CONTEXT_LENGTH = "4096"
$env:OLLAMA_KEEP_ALIVE = "0"
$env:OLLAMA_MODELS = Join-Path $env:LOCALAPPDATA "OdooOps/ollama-models"
$runtimeProcess = Start-Process -FilePath $runtime -ArgumentList "serve" -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $state "stdout.log") -RedirectStandardError (Join-Path $state "stderr.log")
@{ pid = $runtimeProcess.Id; executable = $runtime; models = $env:OLLAMA_MODELS } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $state "process.json") -Encoding utf8
Write-Output "Local-only Ollama started; process metadata saved under local/ollama-runtime."
