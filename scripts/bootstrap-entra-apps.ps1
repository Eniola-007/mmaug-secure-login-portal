[CmdletBinding()]
param(
    [string]$TenantId = '71beefd7-29f4-4b9e-9cb2-e78b5dc851ad',
    [string]$FrontendUrl = '',
    [string]$ApiDisplayName = 'mmaug-secure-login-api',
    [string]$SpaDisplayName = 'mmaug-secure-login-spa',
    [string]$OutputPath = 'entra-apps.json'
)

$ErrorActionPreference = 'Stop'
$GraphBase = 'https://graph.microsoft.com/v1.0'

$currentTenant = (& az account show --query tenantId --output tsv).Trim()
if ($LASTEXITCODE -ne 0 -or $currentTenant -ne $TenantId) {
    throw "Azure CLI must be signed into tenant $TenantId before directory bootstrap."
}

function Invoke-Graph {
    param(
        [Parameter(Mandatory)] [string]$Method,
        [Parameter(Mandatory)] [string]$Uri,
        [object]$Body
    )

    $arguments = @('rest', '--method', $Method, '--url', $Uri, '--output', 'json')
    if ($null -ne $Body) {
        $json = $Body | ConvertTo-Json -Depth 20 -Compress
        $arguments += @('--headers', 'Content-Type=application/json', '--body', $json)
    }

    $raw = & az @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Microsoft Graph request failed: $Method $Uri"
    }
    $text = ($raw | Out-String).Trim()
    if (-not $text) {
        return $null
    }
    return $text | ConvertFrom-Json
}

function Get-OneGraphObject {
    param(
        [Parameter(Mandatory)] [ValidateSet('applications', 'servicePrincipals')] [string]$Collection,
        [Parameter(Mandatory)] [string]$Filter
    )

    $encodedFilter = [Uri]::EscapeDataString($Filter)
    $response = Invoke-Graph -Method GET -Uri "$GraphBase/$Collection`?`$filter=$encodedFilter"
    $items = @($response.value)
    if ($items.Count -gt 1) {
        throw "More than one $Collection object matched '$Filter'. Resolve duplicates before rerunning."
    }
    if ($items.Count -eq 1) {
        return $items[0]
    }
    return $null
}

function Ensure-Application {
    param([Parameter(Mandatory)] [string]$DisplayName)

    $escapedName = $DisplayName.Replace("'", "''")
    $application = Get-OneGraphObject -Collection applications -Filter "displayName eq '$escapedName'"
    if ($null -eq $application) {
        $application = Invoke-Graph -Method POST -Uri "$GraphBase/applications" -Body @{
            displayName    = $DisplayName
            signInAudience = 'AzureADandPersonalMicrosoftAccount'
            api            = @{ requestedAccessTokenVersion = 2 }
        }
    }
    return Invoke-Graph -Method GET -Uri "$GraphBase/applications/$($application.id)"
}

function Ensure-ServicePrincipal {
    param([Parameter(Mandatory)] [string]$AppId)

    $servicePrincipal = Get-OneGraphObject -Collection servicePrincipals -Filter "appId eq '$AppId'"
    if ($null -eq $servicePrincipal) {
        $servicePrincipal = Invoke-Graph -Method POST -Uri "$GraphBase/servicePrincipals" -Body @{
            appId = $AppId
        }
    }
    return $servicePrincipal
}

if ($FrontendUrl) {
    $frontendUri = [Uri]$FrontendUrl
    if ($frontendUri.Scheme -ne 'https') {
        throw 'FrontendUrl must use HTTPS. Localhost is added separately.'
    }
}

$apiApplication = Ensure-Application -DisplayName $ApiDisplayName
$existingScopes = @($apiApplication.api.oauth2PermissionScopes)
$accessScope = $existingScopes | Where-Object value -eq 'access_as_user' | Select-Object -First 1
if ($null -eq $accessScope) {
    $accessScope = [ordered]@{
        id                          = [guid]::NewGuid().ToString()
        value                       = 'access_as_user'
        type                        = 'User'
        isEnabled                   = $true
        adminConsentDisplayName     = 'Access the MMAUG Secure Login API'
        adminConsentDescription     = 'Allow the portal to access the MMAUG API as the signed-in user.'
        userConsentDisplayName      = 'Access the MMAUG school portal'
        userConsentDescription      = 'Allow the portal to access its API on your behalf.'
    }
}
$scopeId = [string]$accessScope.id
$scopes = @($existingScopes | Where-Object value -ne 'access_as_user') + @($accessScope)

Invoke-Graph -Method PATCH -Uri "$GraphBase/applications/$($apiApplication.id)" -Body @{
    signInAudience = 'AzureADandPersonalMicrosoftAccount'
    identifierUris = @("api://$($apiApplication.appId)")
    api = @{
        requestedAccessTokenVersion = 2
        oauth2PermissionScopes       = $scopes
        preAuthorizedApplications   = @($apiApplication.api.preAuthorizedApplications)
    }
} | Out-Null
$apiApplication = Invoke-Graph -Method GET -Uri "$GraphBase/applications/$($apiApplication.id)"
$apiServicePrincipal = Ensure-ServicePrincipal -AppId $apiApplication.appId

$redirectUris = @('http://localhost:5173')
if ($FrontendUrl) {
    $redirectUris += $FrontendUrl.TrimEnd('/')
}
$spaApplication = Ensure-Application -DisplayName $SpaDisplayName
Invoke-Graph -Method PATCH -Uri "$GraphBase/applications/$($spaApplication.id)" -Body @{
    signInAudience = 'AzureADandPersonalMicrosoftAccount'
    api = @{ requestedAccessTokenVersion = 2 }
    spa = @{ redirectUris = @($redirectUris | Select-Object -Unique) }
    requiredResourceAccess = @(
        @{
            resourceAppId  = $apiApplication.appId
            resourceAccess = @(@{ id = $scopeId; type = 'Scope' })
        }
    )
} | Out-Null
$spaApplication = Invoke-Graph -Method GET -Uri "$GraphBase/applications/$($spaApplication.id)"
$spaServicePrincipal = Ensure-ServicePrincipal -AppId $spaApplication.appId

$apiApplication = Invoke-Graph -Method GET -Uri "$GraphBase/applications/$($apiApplication.id)"
$preAuthorized = @($apiApplication.api.preAuthorizedApplications | Where-Object appId -ne $spaApplication.appId)
$preAuthorized += @{
    appId                  = $spaApplication.appId
    delegatedPermissionIds = @($scopeId)
}
Invoke-Graph -Method PATCH -Uri "$GraphBase/applications/$($apiApplication.id)" -Body @{
    api = @{
        requestedAccessTokenVersion = 2
        oauth2PermissionScopes       = @($apiApplication.api.oauth2PermissionScopes)
        preAuthorizedApplications   = $preAuthorized
    }
} | Out-Null

$grantFilter = "clientId eq '$($spaServicePrincipal.id)'"
$encodedGrantFilter = [Uri]::EscapeDataString($grantFilter)
$grantResponse = Invoke-Graph -Method GET -Uri "$GraphBase/oauth2PermissionGrants`?`$filter=$encodedGrantFilter"
$grant = @($grantResponse.value) | Where-Object {
    $_.resourceId -eq $apiServicePrincipal.id -and $_.consentType -eq 'AllPrincipals'
} | Select-Object -First 1
if ($null -eq $grant) {
    Invoke-Graph -Method POST -Uri "$GraphBase/oauth2PermissionGrants" -Body @{
        clientId   = $spaServicePrincipal.id
        consentType = 'AllPrincipals'
        resourceId = $apiServicePrincipal.id
        scope       = 'access_as_user'
    } | Out-Null
} elseif (-not (($grant.scope -split ' ') -contains 'access_as_user')) {
    $updatedScopes = (@($grant.scope -split ' ') + 'access_as_user' | Where-Object { $_ }) -join ' '
    Invoke-Graph -Method PATCH -Uri "$GraphBase/oauth2PermissionGrants/$($grant.id)" -Body @{
        scope = $updatedScopes
    } | Out-Null
}

$result = [ordered]@{
    tenant_id                        = $TenantId
    sign_in_audience                 = 'AzureADandPersonalMicrosoftAccount'
    authority                        = 'https://login.microsoftonline.com/common'
    api_client_id                    = $apiApplication.appId
    api_application_object_id        = $apiApplication.id
    api_enterprise_app_object_id     = $apiServicePrincipal.id
    api_scope                        = "api://$($apiApplication.appId)/access_as_user"
    spa_client_id                    = $spaApplication.appId
    spa_application_object_id        = $spaApplication.id
    spa_enterprise_app_object_id     = $spaServicePrincipal.id
    spa_redirect_uris                = @($redirectUris | Select-Object -Unique)
    delegated_consent                = 'AllPrincipals'
}

$result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $OutputPath -Encoding utf8
$result | ConvertTo-Json -Depth 10
