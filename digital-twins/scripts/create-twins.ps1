$dtName = "moiz-dt-instance"

function New-JsonFile($obj) {
    $path = [System.IO.Path]::GetTempFileName() + ".json"
    $obj | ConvertTo-Json -Compress | Out-File -FilePath $path -Encoding utf8
    return $path
}

Write-Host "Creating Room twin..."
$roomProps = New-JsonFile @{ roomNumber="101"; floor=1; status="active" }
az dt twin create `
  --dt-name $dtName `
  --twin-id "room101" `
  --model-id "dtmi:moiz:smartbuilding:Room;1" `
  --properties @$roomProps

Write-Host "Creating HVAC twin..."
$hvacProps = New-JsonFile @{ powerState="on"; status="active" }
az dt twin create `
  --dt-name $dtName `
  --twin-id "hvac101" `
  --model-id "dtmi:moiz:smartbuilding:HVACUnit;1" `
  --properties @$hvacProps

Write-Host "Creating Temperature Sensor twin..."
$tempProps = New-JsonFile @{ currentTemperature=22.5; status="active" }
az dt twin create `
  --dt-name $dtName `
  --twin-id "tempSensor101" `
  --model-id "dtmi:moiz:smartbuilding:TemperatureSensor;1" `
  --properties @$tempProps

Write-Host "Creating CO2 Sensor twin..."
$co2Props = New-JsonFile @{ currentCO2ppm=450; status="active" }
az dt twin create `
  --dt-name $dtName `
  --twin-id "co2Sensor101" `
  --model-id "dtmi:moiz:smartbuilding:CO2Sensor;1" `
  --properties @$co2Props

Write-Host "Creating relationships..."
az dt twin relationship create `
  --dt-name $dtName `
  --twin-id "room101" `
  --relationship-id "room101-hvac" `
  --relationship "hasHVAC" `
  --target "hvac101"

az dt twin relationship create `
  --dt-name $dtName `
  --twin-id "hvac101" `
  --relationship-id "hvac101-temp" `
  --relationship "hasSensor" `
  --target "tempSensor101"

az dt twin relationship create `
  --dt-name $dtName `
  --twin-id "hvac101" `
  --relationship-id "hvac101-co2" `
  --relationship "hasSensor" `
  --target "co2Sensor101"

Write-Host "Done."