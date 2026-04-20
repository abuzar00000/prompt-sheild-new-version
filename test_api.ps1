# Run while the server is up: .\test_api.ps1
# Optional: $base = "http://127.0.0.1:8765"
param([string]$Base = "http://127.0.0.1:8080")

$ErrorActionPreference = "Stop"
Write-Host "GET $Base/health"
(Invoke-RestMethod -Uri "$Base/health" | ConvertTo-Json -Compress)

Write-Host "`nPOST $Base/sanitize (skip_rewrite=true)"
$body = '{"prompt":"Email jane.doe@mail.mil about DOC-2024-AB.","skip_rewrite":true}'
(Invoke-RestMethod -Uri "$Base/sanitize" -Method Post -ContentType "application/json; charset=utf-8" -Body $body | ConvertTo-Json -Depth 8 -Compress)

Write-Host "`nPOST $Base/sanitize (skip_rewrite=false, needs GROK_API_KEY)"
$body2 = '{"prompt":"Email jane.doe@mail.mil about the project.","skip_rewrite":false}'
(Invoke-RestMethod -Uri "$Base/sanitize" -Method Post -ContentType "application/json; charset=utf-8" -Body $body2 | ConvertTo-Json -Depth 8 -Compress)
