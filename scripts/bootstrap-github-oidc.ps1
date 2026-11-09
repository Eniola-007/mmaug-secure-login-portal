[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)] [string] $GitHubOwner,
    [Parameter(Mandatory)] [string] $GitHubRepository,
    [string] $GitHubOwnerId = '78024150',
    [string] $GitHubRepositoryId = '1450348387',
    [ValidateSet('development', 'uat', 'production')] [string] $Environment = 'development',
    [string] $ResourceGroup = 'rg_mmaug_high_school',
    [string] $IdentityName = 'id-mmaug-secure-login-portal'
)

$ErrorActionPreference = 'Stop'
$subject = "repo:$GitHubOwner@$GitHubOwnerId/$GitHubRepository@$GitHubRepositoryId`:environment:$Environment"
$credentialName = "github-$Environment-repository-id"

$identityJson = az identity show --resource-group $ResourceGroup --name $IdentityName --output json 2>$null
if (-not $identityJson) {
    throw "Approved managed identity '$IdentityName' was not found in '$ResourceGroup'. This script will not create a second identity."
}
$identity = $identityJson | ConvertFrom-Json

if ($PSCmdlet.ShouldProcess($credentialName, "Trust GitHub subject $subject")) {
    $existing = az identity federated-credential show --resource-group $ResourceGroup --identity-name $IdentityName --name $credentialName --output json 2>$null
    if (-not $existing) {
        az identity federated-credential create `
            --resource-group $ResourceGroup `
            --identity-name $IdentityName `
            --name $credentialName `
            --issuer 'https://token.actions.githubusercontent.com' `
            --subject $subject `
            --audiences 'api://AzureADTokenExchange' | Out-Null
    }
}

$identity = az identity show --resource-group $ResourceGroup --name $IdentityName --output json | ConvertFrom-Json
[pscustomobject]@{
    AZURE_CLIENT_ID       = $identity.clientId
    AZURE_TENANT_ID       = $identity.tenantId
    AZURE_SUBSCRIPTION_ID = (az account show --query id --output tsv)
    GitHubSubject         = $subject
}
