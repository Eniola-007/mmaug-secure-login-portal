[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)] [string] $GitHubOwner,
    [Parameter(Mandatory)] [string] $GitHubRepository,
    [ValidateSet('development', 'uat', 'production')] [string] $Environment = 'development',
    [string] $ResourceGroup = 'rg_mmaug_high_school',
    [string] $Location = 'northeurope',
    [string] $IdentityName = 'id-mmaug-github-deploy'
)

$ErrorActionPreference = 'Stop'
$subject = "repo:$GitHubOwner/$GitHubRepository`:environment:$Environment"
$credentialName = "github-$Environment"

if ($PSCmdlet.ShouldProcess($IdentityName, 'Create deployment identity if absent')) {
    $identity = az identity show --resource-group $ResourceGroup --name $IdentityName --output json 2>$null | ConvertFrom-Json
    if (-not $identity) {
        $identity = az identity create --resource-group $ResourceGroup --name $IdentityName --location $Location --output json | ConvertFrom-Json
    }
}

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
