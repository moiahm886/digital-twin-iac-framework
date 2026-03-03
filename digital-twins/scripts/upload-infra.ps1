$rg = "rg-moiz-dt"
$storage = ("moizdtst" + (Get-Random -Maximum 99999))  # must be lowercase

az deployment group create `
  -g rg-moiz-dt `
  -f "../../infrastructure/main.bicep" `
  -p storageAccountName=$storage `
     adtDataOwnerRoleGuid="bcd981a7-7f74-457b-83e1-cceb9e632ffe" `
     dtName="moiz-dt-instance" `
     ehNamespaceName="moiz-ehns" `
     functionAppName="moiz-dt-func"