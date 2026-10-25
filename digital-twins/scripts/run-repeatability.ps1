<#
  Repeatability experiment.

  Deploys the same Bicep definition three times into three fresh resource
  groups, records wall clock and exit status for each, exports the resulting
  resource state, normalises the parts that are expected to differ, and diffs
  them.

  Run step 0 (Test-Export) once before the full run. If the export path is
  broken on your subscription the script falls back to a resource inventory,
  but you want to know that before three deployments are sitting there.

  Usage:
      .\run-repeatability.ps1 -TestExportOnly -ExistingRg rg-dt-framework
      .\run-repeatability.ps1
#>

param(
    [switch]$TestExportOnly,
    [string]$ExistingRg       = "rg-dt-framework",
    [string]$Location         = "westeurope",
    [string]$TemplateFile     = "../../infrastructure/main.bicep",
    [string]$AdtRole          = $null,
    [int]$Runs                = 3,
    [string]$OutDir           = "repeat-results"
)

$ErrorActionPreference = "Continue"   # az writes warnings to stderr; Stop would abort on them
$env:AZURE_CORE_ONLY_SHOW_ERRORS = "true"


$PY = if (Get-Command python -ErrorAction SilentlyContinue) { "python" }
      elseif (Get-Command py -ErrorAction SilentlyContinue) { "py" }
      else { $null }

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function New-Suffix {
    -join ((48..57) + (97..122) | Get-Random -Count 8 | ForEach-Object { [char]$_ })
}

# ---------------------------------------------------------------- step 0
if ($TestExportOnly) {
    $exists = az group exists --name $ExistingRg -o tsv
    if ($exists -ne "true") {
        Write-Host "Resource group '$ExistingRg' does not exist." -ForegroundColor Yellow
        Write-Host "Nothing to test against. Either name an existing group with"
        Write-Host "-ExistingRg, or skip this step and run the full experiment:"
        Write-Host "    .\run-repeatability.ps1" -ForegroundColor Cyan
        Write-Host "Each deployment exports its own group and falls back on its own,"
        Write-Host "so skipping this step costs you nothing."
        Write-Host "`nGroups in this subscription:"
        az group list --query "[].name" -o tsv
        return
    }

    Write-Host "Testing az group export on $ExistingRg ..."
    $out = Join-Path $OutDir "test-export.json"
    az group export --name $ExistingRg --skip-all-params | Set-Content $out
    if ($LASTEXITCODE -ne 0) {
        Write-Host "export FAILED on an existing group. The full run will use the" -ForegroundColor Yellow
        Write-Host "resource-list fallback, which is weaker evidence but still usable." -ForegroundColor Yellow
    } else {
        $n = (Select-String -Path $out -Pattern '"type"' -AllMatches).Matches.Count
        Write-Host "export OK. $n type entries found." -ForegroundColor Green
        Write-Host "If that number looks far too low, use the fallback anyway."
    }
    return
}

# ---------------------------------------------------------------- role id
# Resolution order:
#   1. -AdtRole on the command line
#   2. $env:ADT_ROLE_GUID
#   3. looked up from Azure
# Nothing is hardcoded, so nothing needs committing.
if (-not $AdtRole) { $AdtRole = $env:ADT_ROLE_GUID }
if (-not $AdtRole) {
    Write-Host "Looking up the Azure Digital Twins Data Owner role id ..."
    $AdtRole = az role definition list `
        --name "Azure Digital Twins Data Owner" `
        --query "[0].name" -o tsv
    if ($LASTEXITCODE -ne 0 -or -not $AdtRole) {
        Write-Error "Could not resolve the role id. Pass -AdtRole or set ADT_ROLE_GUID."
        return
    }
}
$AdtRole = $AdtRole.Trim()
Write-Host "Role id: $AdtRole"

# ---------------------------------------------------------------- step 1
$suffixes = 1..$Runs | ForEach-Object { New-Suffix }
$timings  = @()

foreach ($s in $suffixes) {
    $rg = "rg-repeat-$s"
    Write-Host "`n=== deploying $rg ===" -ForegroundColor Cyan

    az group create -n $rg -l $Location -o none

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    az deployment group create `
        -g $rg `
        -f $TemplateFile `
        -p prefix="dt$s" `
           storageAccountName="dtst$s" `
           adtDataOwnerRoleGuid=$AdtRole `
        -o none
    $status = $LASTEXITCODE
    $sw.Stop()

    $timings += [pscustomobject]@{
        suffix  = $s
        rg      = $rg
        seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1)
        status  = $status
    }
    Write-Host ("  {0}s, exit {1}" -f [math]::Round($sw.Elapsed.TotalSeconds,1), $status)
}

$timings | Export-Csv (Join-Path $OutDir "deploy-times.csv") -NoTypeInformation
$timings | Format-Table -AutoSize

$ok = @($timings | Where-Object { $_.status -eq 0 })
if ($ok.Count -gt 1) {
    $mean = ($ok.seconds | Measure-Object -Average).Average
    $sd = if ($ok.Count -gt 1) {
        [math]::Sqrt((($ok.seconds | ForEach-Object { [math]::Pow($_ - $mean,2) }) |
            Measure-Object -Sum).Sum / ($ok.Count - 1))
    } else { 0 }
    Write-Host ("`nSucceeded {0}/{1}  mean {2:N1}s  sd {3:N1}s  min {4:N1}s  max {5:N1}s" -f `
        $ok.Count, $Runs, $mean, $sd,
        ($ok.seconds | Measure-Object -Minimum).Minimum,
        ($ok.seconds | Measure-Object -Maximum).Maximum) -ForegroundColor Green
}

# ---------------------------------------------------------------- step 2
foreach ($t in $ok) {
    $raw = Join-Path $OutDir "state-$($t.suffix).json"
    az group export --name $t.rg --skip-all-params | Set-Content $raw
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $raw) -or (Get-Item $raw).Length -lt 200) {
        Write-Host "  export failed for $($t.rg), using resource inventory" -ForegroundColor Yellow
        az resource list -g $t.rg `
            --query "sort_by([].{type:type,name:name,location:location,sku:sku,kind:kind}, &type)" `
            -o json | Set-Content $raw
    }
}

# ---------------------------------------------------------------- step 3
$py = Join-Path $OutDir "_normalise.py"
@'
import json, re, sys
suffix = sys.argv[1]
text = open(sys.argv[2], encoding="utf-8").read()
text = text.replace(suffix, "SUFFIX")
text = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "GUID", text)
print(json.dumps(json.loads(text), sort_keys=True, indent=2))
'@ | Set-Content $py -Encoding UTF8

foreach ($t in $ok) {
    $raw  = Join-Path $OutDir "state-$($t.suffix).json"
    $norm = Join-Path $OutDir "norm-$($t.suffix).json"
    if ($PY) {
        & $PY -I $py $t.suffix $raw | Set-Content $norm
    } else {
        # no python: normalise with plain text substitution, no key sorting
        (Get-Content $raw -Raw).Replace($t.suffix, "SUFFIX") `
            -replace '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'GUID' |
            Set-Content $norm
    }
}

Write-Host "`n=== diffs ===" -ForegroundColor Cyan
$base = Join-Path $OutDir "norm-$($ok[0].suffix).json"
for ($i = 1; $i -lt $ok.Count; $i++) {
    $other = Join-Path $OutDir "norm-$($ok[$i].suffix).json"
    $d = Compare-Object (Get-Content $base) (Get-Content $other)
    if ($null -eq $d) {
        Write-Host "  deployment 1 vs $($i+1): IDENTICAL" -ForegroundColor Green
    } else {
        Write-Host "  deployment 1 vs $($i+1): $($d.Count) differing lines" -ForegroundColor Yellow
        $d | Select-Object -First 25 | Format-Table -AutoSize
    }
}

Write-Host "`nResource groups left up on purpose. Delete when done:"
$ok | ForEach-Object { Write-Host "  az group delete --name $($_.rg) --yes --no-wait" }