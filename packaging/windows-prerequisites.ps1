$ErrorActionPreference = 'Stop'
$target = Join-Path $PSScriptRoot '..\build\prerequisites'
New-Item -ItemType Directory -Force -Path $target | Out-Null
$installer = Join-Path $target 'MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
# Microsoft's Evergreen Standalone x64 distribution link.
Invoke-WebRequest 'https://go.microsoft.com/fwlink/?linkid=2124701' -OutFile $installer
$signature = Get-AuthenticodeSignature $installer
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
    throw 'WebView2 installer does not have a valid Microsoft signature'
}
Get-FileHash $installer -Algorithm SHA256
if (-not (Test-Path 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe')) {
    choco install innosetup --yes --no-progress
    if ($LASTEXITCODE -ne 0) { throw 'Unable to install Inno Setup' }
}
