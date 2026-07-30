# ngrok_start.ps1
# RGA Ngrok Startup Script
# Purpose:
# - Start ngrok using the reserved RGA domain
# - Keep FastAPI backend separate from tunnel lifecycle

$ErrorActionPreference = 'Stop'

$ReservedDomain = 'leptophyllous-nick-unobscured.ngrok-free.dev'
$BackendPort = 8000

Write-Host ''
Write-Host '=== Rhythm Game Assistant ngrok Startup ===' -ForegroundColor Cyan
Write-Host "Domain : https://$ReservedDomain"
Write-Host "Backend: http://127.0.0.1:$BackendPort"
Write-Host ''
Write-Host 'Prerequisites:' -ForegroundColor Yellow
Write-Host '  1. FastAPI backend already running'
Write-Host '  2. ngrok authenticated (authtoken configured)'
Write-Host ''

ngrok http --domain=$ReservedDomain $BackendPort
