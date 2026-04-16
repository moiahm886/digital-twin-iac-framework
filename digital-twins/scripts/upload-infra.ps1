$rg = "rg-dt-framework"
$storage = ("dtframeworkst" + (Get-Random -Maximum 99999))  # must be lowercase

az deployment group create `
  -g rg-dt-framework `
  -f "../../infrastructure/main.bicep" `
  -p storageAccountName=$storage `
     adtDataOwnerRoleGuid="bcd981a7-7f74-457b-83e1-cceb9e632ffe" `
     dtName="dtframework-dt-instance" `
     ehNamespaceName="dtframework-ehns" `
     functionAppName="dtframework-dt-func"