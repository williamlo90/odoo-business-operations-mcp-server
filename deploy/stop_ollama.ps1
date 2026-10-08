$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
$metadata = Get-Content -Raw -LiteralPath (Join-Path $projectRoot "local/ollama-runtime/process.json") | ConvertFrom-Json
$runtimeProcess = Get-Process -Id $metadata.pid -ErrorAction SilentlyContinue
if ($runtimeProcess) {
    if ($runtimeProcess.Path -ne $metadata.executable) { throw "Process identity changed; refusing to stop it." }
    Stop-Process -Id $runtimeProcess.Id
}
Write-Output "Project Ollama runtime stopped; downloaded models preserved."
