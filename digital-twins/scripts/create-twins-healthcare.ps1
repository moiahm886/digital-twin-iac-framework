$dtName = "moiz-dt-instance"

# Helper to create JSON files
function New-JsonFile($obj) {
    $path = [System.IO.Path]::GetTempFileName() + ".json"
    $obj | ConvertTo-Json -Compress | Out-File -FilePath $path -Encoding utf8
    return $path
}

Write-Host "Creating Patient Monitor twin..."
$pmProps = New-JsonFile @{ patientId = "P-001" }
az dt twin create `
  --dt-name $dtName `
  --twin-id "patientMonitor001" `
  --model-id "dtmi:moiz:healthcare:PatientMonitor;1" `
  --properties @$pmProps

Write-Host "Creating Monitoring Unit twin..."
$muProps = New-JsonFile @{}
az dt twin create `
  --dt-name $dtName `
  --twin-id "monitoringUnit001" `
  --model-id "dtmi:moiz:healthcare:MonitoringUnit;1" `
  --properties @$muProps

Write-Host "Creating Blood Pressure Sensor twin..."
$bpProps = New-JsonFile @{ currentSystolic = 120; currentDiastolic = 80 }
az dt twin create `
  --dt-name $dtName `
  --twin-id "bpSensor001" `
  --model-id "dtmi:moiz:healthcare:BloodPressureSensor;1" `
  --properties @$bpProps

Write-Host "Creating Heart Rate Sensor twin..."
$hrProps = New-JsonFile @{ currentBPM = 72 }
az dt twin create `
  --dt-name $dtName `
  --twin-id "hrSensor001" `
  --model-id "dtmi:moiz:healthcare:HeartRateSensor;1" `
  --properties @$hrProps

Write-Host "Creating relationships..."
az dt twin relationship create `
  --dt-name $dtName `
  --twin-id "patientMonitor001" `
  --relationship-id "pm001-mu001" `
  --relationship "hasMonitoringUnit" `
  --target "monitoringUnit001"

az dt twin relationship create `
  --dt-name $dtName `
  --twin-id "monitoringUnit001" `
  --relationship-id "mu001-bp001" `
  --relationship "hasSensor" `
  --target "bpSensor001"

az dt twin relationship create `
  --dt-name $dtName `
  --twin-id "monitoringUnit001" `
  --relationship-id "mu001-hr001" `
  --relationship "hasSensor" `
  --target "hrSensor001"

Write-Host "Healthcare domain twins created."