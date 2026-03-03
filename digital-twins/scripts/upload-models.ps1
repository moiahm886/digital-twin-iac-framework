$dtName = "moiz-dt-instance"

az dt model create --dt-name $dtName --from-directory "../models/core"
az dt model create --dt-name $dtName --from-directory "../models/smartbuilding"