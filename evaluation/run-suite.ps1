param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("consumption", "premium")]
    [string]$Tier,

    [int[]]$Rates   = @(50, 200, 500, 1000),
    [int]$Runs      = 2,
    [int]$Count     = 3000,
    [int]$Warmup    = 500,
    [int]$GapSeconds = 45
)

$prefix = if ($Tier -eq "consumption") { "c" } else { "p" }
$log    = "results\run-log-$Tier.txt"
New-Item -ItemType Directory -Force -Path results | Out-Null

"=== $Tier suite started $(Get-Date -Format s) ===" | Tee-Object -FilePath $log -Append

foreach ($rate in $Rates) {
    for ($r = 1; $r -le $Runs; $r++) {
        $runId = "$prefix-$rate-$r"
        "--- $runId ---" | Tee-Object -FilePath $log -Append

        python producer.py --rate $rate --count $Count --warmup $Warmup --run-id $runId `
            2>&1 | Tee-Object -FilePath $log -Append

        # let the consumer drain and the plan scale back down before the next run,
        # so one run does not contaminate the next
        "waiting $GapSeconds s for drain" | Tee-Object -FilePath $log -Append
        Start-Sleep -Seconds $GapSeconds
    }
}

"=== $Tier suite finished $(Get-Date -Format s) ===" | Tee-Object -FilePath $log -Append
Write-Host ""
Write-Host "Done. Wait 3-5 minutes for App Insights ingestion, then run collect-results.ps1"