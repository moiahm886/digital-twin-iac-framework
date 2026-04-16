$dtName = "dtframework-dt-instance"

az dt model create --dt-name $dtName --from-directory "../models/core"
az dt model create --dt-name $dtName --from-directory "../models/smartbuilding"
az dt model create --dt-name $dtName --from-directory "../models/healthcare"
az dt model create --dt-name $dtName --from-directory "../models/vehicle"