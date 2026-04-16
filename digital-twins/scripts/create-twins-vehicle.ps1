$dtName = "dtframework-dt-instance"

function New-JsonFile($obj) {
    $path = [System.IO.Path]::GetTempFileName() + ".json"
    $obj | ConvertTo-Json -Compress | Out-File -FilePath $path -Encoding utf8
    return $path
}

Write-Host "Creating Autonomous Vehicle twin..."
$vehicleProps = New-JsonFile @{ vin = "VIN-001"; model = "Model-X" }
az dt twin create `
  --dt-name $dtName `
  --twin-id "vehicle001" `
  --model-id "dtmi:dtframework:vehicle:AutonomousVehicle;1" `
  --properties @$vehicleProps

Write-Host "Creating Powertrain twin..."
$ptProps = New-JsonFile @{}
az dt twin create `
  --dt-name $dtName `
  --twin-id "powertrain001" `
  --model-id "dtmi:dtframework:vehicle:Powertrain;1" `
  --properties @$ptProps

Write-Host "Creating Battery Sensor twin..."
$battProps = New-JsonFile @{ currentChargePercentage = 87.5 }
az dt twin create `
  --dt-name $dtName `
  --twin-id "batterySensor001" `
  --model-id "dtmi:dtframework:vehicle:BatterySensor;1" `
  --properties @$battProps

Write-Host "Creating GPS Sensor twin..."
$gpsProps = New-JsonFile @{ currentLatitude = 31.5204; currentLongitude = 74.3587 }
az dt twin create `
  --dt-name $dtName `
  --twin-id "gpsSensor001" `
  --model-id "dtmi:dtframework:vehicle:GPSSensor;1" `
  --properties @$gpsProps

Write-Host "Creating relationships..."
az dt twin relationship create `
  --dt-name $dtName `
  --twin-id "vehicle001" `
  --relationship-id "vehicle001-pt001" `
  --relationship "hasPowertrain" `
  --target "powertrain001"

az dt twin relationship create `
  --dt-name $dtName `
  --twin-id "powertrain001" `
  --relationship-id "pt001-batt001" `
  --relationship "hasSensor" `
  --target "batterySensor001"

az dt twin relationship create `
  --dt-name $dtName `
  --twin-id "powertrain001" `
  --relationship-id "pt001-gps001" `
  --relationship "hasSensor" `
  --target "gpsSensor001"

Write-Host "Autonomous Vehicle domain twins created."