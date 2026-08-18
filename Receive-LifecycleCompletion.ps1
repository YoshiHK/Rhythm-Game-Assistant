param(
    [Parameter(Mandatory)]
    [string]$SessionId
)

python .\tools\github_lifecycle_bridge.py `
    --owner YoshiHK `
    --repo Rhythm-Game-Assistant `
    --poll-completion `
    --session-id $SessionId