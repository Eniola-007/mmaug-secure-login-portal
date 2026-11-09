[CmdletBinding()]
param(
    [string]$InputPath = 'docs/proposal-v4.md',
    [string]$OutputPath = 'MMAUG_Secure_Login_Portal_RFP_Response_v4_Single_Identity_WAF.pdf'
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$inputFile = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot $InputPath))
$outputFile = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot $OutputPath))
$logoFile = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot 'frontend/src/assets/mmaug-logo.png'))
$architectureFile = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot 'docs/architecture-microsoft.svg'))
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

if (-not (Test-Path -LiteralPath $inputFile)) {
    throw "Proposal source was not found: $inputFile"
}
if (-not (Test-Path -LiteralPath $edge)) {
    throw "Microsoft Edge was not found: $edge"
}

$rendered = ConvertFrom-Markdown -Path $inputFile
$logoUri = ([Uri]$logoFile).AbsoluteUri
$architectureUri = ([Uri]$architectureFile).AbsoluteUri
$proposalHtml = $rendered.Html.Replace('src="architecture-microsoft.svg"', "src=`"$architectureUri`"")
$html = @"
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MMAUG Secure Login Portal — Updated Technical Proposal</title>
<style>
  @page { size: A4; margin: 18mm 17mm 20mm; }
  body { color: #14283a; font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.48; }
  .brand { align-items: center; border-bottom: 4px solid #c88a2d; display: flex; gap: 16px; margin-bottom: 24px; padding-bottom: 14px; }
  .brand img { height: 76px; width: 76px; }
  .brand div { color: #0b4969; font-size: 20pt; font-weight: 700; }
  h1 { color: #0b4969; font-size: 24pt; line-height: 1.15; margin: 0 0 12px; }
  h2 { border-bottom: 1px solid #b7c7d3; color: #0b4969; font-size: 15pt; margin: 24px 0 10px; padding-bottom: 4px; page-break-after: avoid; }
  h3 { color: #173f58; font-size: 12pt; page-break-after: avoid; }
  table { border-collapse: collapse; font-size: 9.2pt; margin: 12px 0 18px; width: 100%; }
  th { background: #0b4969; color: white; text-align: left; }
  th, td { border: 1px solid #9eb2c0; padding: 7px; vertical-align: top; }
  tr { page-break-inside: avoid; }
  code { background: #eef3f6; border-radius: 3px; font-family: Consolas, monospace; font-size: 9pt; padding: 1px 3px; }
  li { margin: 3px 0; }
  a { color: #0b628d; }
</style>
</head>
<body>
<div class="brand"><img src="$logoUri" alt="MMAUG logo"><div>MALTA MICROSOFT AI USER GROUP</div></div>
$proposalHtml
</body>
</html>
"@

$temporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$temporaryDirectory = Join-Path $temporaryRoot ("mmaug-proposal-" + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $temporaryDirectory

try {
    $htmlFile = Join-Path $temporaryDirectory 'proposal.html'
    $profileDirectory = Join-Path $temporaryDirectory 'edge-profile'
    $html | Set-Content -LiteralPath $htmlFile -Encoding utf8
    $htmlUri = ([Uri]$htmlFile).AbsoluteUri

    $edgeArguments = @(
        '--headless=new'
        '--disable-gpu'
        '--allow-file-access-from-files'
        '--no-pdf-header-footer'
        "--user-data-dir=$profileDirectory"
        "--print-to-pdf=$outputFile"
        $htmlUri
    )
    $edgeProcess = Start-Process -FilePath $edge -ArgumentList $edgeArguments -Wait -PassThru -WindowStyle Hidden

    for ($attempt = 0; $attempt -lt 40 -and -not (Test-Path -LiteralPath $outputFile); $attempt++) {
        Start-Sleep -Milliseconds 250
    }

    if (-not (Test-Path -LiteralPath $outputFile)) {
        throw "Edge exited with code $($edgeProcess.ExitCode) without producing the expected PDF: $outputFile"
    }
    Get-Item -LiteralPath $outputFile | Select-Object FullName, Length, LastWriteTime
}
finally {
    $resolvedTemporaryDirectory = [System.IO.Path]::GetFullPath($temporaryDirectory)
    if ($resolvedTemporaryDirectory.StartsWith($temporaryRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $resolvedTemporaryDirectory -Recurse -Force -ErrorAction SilentlyContinue
    }
}
