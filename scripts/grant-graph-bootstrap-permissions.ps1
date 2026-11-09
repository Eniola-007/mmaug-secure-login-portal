[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$ManagedIdentityObjectId = '6d15404b-a6d8-4019-b638-609f1c75723d'
)

$ErrorActionPreference = 'Stop'
$graphBase = 'https://graph.microsoft.com/v1.0'
$graphAppId = '00000003-0000-0000-c000-000000000000'
$requiredRoles = @('Application.ReadWrite.All', 'DelegatedPermissionGrant.ReadWrite.All')

function Invoke-GraphRequest {
    param(
        [Parameter(Mandatory)] [string]$Method,
        [Parameter(Mandatory)] [string]$Uri,
        [object]$Body
    )

    $arguments = @('rest', '--method', $Method, '--url', $Uri, '--output', 'json')
    $bodyFile = $null
    try {
        if ($null -ne $Body) {
            $bodyFile = [System.IO.Path]::GetTempFileName()
            $Body | ConvertTo-Json -Depth 10 -Compress | Set-Content -LiteralPath $bodyFile -Encoding utf8NoBOM
            $arguments += @('--headers', 'Content-Type=application/json', '--body', "@$bodyFile")
        }
        $raw = & az @arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Microsoft Graph request failed: $Method $Uri"
        }
        $text = ($raw | Out-String).Trim()
        if ($text) {
            return $text | ConvertFrom-Json
        }
    }
    finally {
        if ($bodyFile -and (Test-Path -LiteralPath $bodyFile)) {
            Remove-Item -LiteralPath $bodyFile -Force
        }
    }
}

$filter = [Uri]::EscapeDataString("appId eq '$graphAppId'")
$graphServicePrincipals = Invoke-GraphRequest -Method GET -Uri "$graphBase/servicePrincipals?`$filter=$filter"
$graphServicePrincipal = @($graphServicePrincipals.value) | Select-Object -First 1
if (-not $graphServicePrincipal) {
    throw 'Microsoft Graph service principal was not found in this tenant.'
}

$assignments = Invoke-GraphRequest -Method GET -Uri "$graphBase/servicePrincipals/$ManagedIdentityObjectId/appRoleAssignments"
foreach ($roleName in $requiredRoles) {
    $role = @($graphServicePrincipal.appRoles) | Where-Object {
        $_.value -eq $roleName -and $_.isEnabled -and $_.allowedMemberTypes -contains 'Application'
    } | Select-Object -First 1
    if (-not $role) {
        throw "Microsoft Graph application role was not found: $roleName"
    }

    $exists = @($assignments.value) | Where-Object {
        $_.resourceId -eq $graphServicePrincipal.id -and $_.appRoleId -eq $role.id
    }
    if ($exists) {
        Write-Host "$roleName is already assigned."
        continue
    }

    if ($PSCmdlet.ShouldProcess($ManagedIdentityObjectId, "Assign Microsoft Graph $roleName")) {
        Invoke-GraphRequest -Method POST -Uri "$graphBase/servicePrincipals/$ManagedIdentityObjectId/appRoleAssignments" -Body @{
            principalId = $ManagedIdentityObjectId
            resourceId  = $graphServicePrincipal.id
            appRoleId   = $role.id
        } | Out-Null
        Write-Host "Assigned $roleName."
    }
}

Write-Host 'Graph bootstrap permissions are ready. Remove them after the Entra applications are finalized.'
