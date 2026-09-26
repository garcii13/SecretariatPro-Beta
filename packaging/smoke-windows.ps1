# Install, launch and uninstall the actual installers on the disposable CI runner.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
foreach ($product in @('Live', 'Manager')) {
    $name = "SecretariatPro $product"
    $target = Join-Path $env:RUNNER_TEMP "Installed-$product"
    $installer = @(Get-ChildItem "$root\release\SecretariatPro-$product-*-windows-x64-setup.exe")
    if ($installer.Count -ne 1) { throw "Expected one installer for $product" }
    $installLog = Join-Path $root "release\smoke-install-$product.log"
    $setup = Start-Process $installer[0].FullName -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$target`"", "/LOG=`"$installLog`"") -Wait -PassThru
    if ($setup.ExitCode -notin @(0, 3010)) { throw "Installer failed: $($setup.ExitCode)" }
    $port = if ($product -eq 'Live') { 18765 } else { 18766 }
    $arguments = @('--port', "$port")
    if ($product -eq 'Live') { $arguments += @('--host', '127.0.0.1', '--windowed') }
    $app = Start-Process (Join-Path $target "$name.exe") -ArgumentList $arguments -PassThru
    try {
        $health = $null
        for ($attempt = 0; $attempt -lt 90; $attempt++) {
            if ($app.HasExited) { throw "$name exited before its backend became available" }
            try { $health = Invoke-RestMethod "http://127.0.0.1:$port/api/health" -TimeoutSec 2; break } catch { Start-Sleep -Seconds 1 }
        }
        if (-not $health) { throw "$name backend did not start" }
        $page = Invoke-WebRequest "http://127.0.0.1:$port/" -UseBasicParsing
        if ($page.StatusCode -ne 200) { throw "$name UI is unavailable" }
        Start-Sleep -Seconds 5
        $app.Refresh()
        if ($app.HasExited -or $app.MainWindowHandle -eq 0) { throw "$name native window did not open" }
        $health | ConvertTo-Json | Set-Content "$root\release\smoke-health-$product.log"
    } finally {
        if (-not $app.HasExited) {
            $app.CloseMainWindow() | Out-Null
            if (-not $app.WaitForExit(15000)) { Stop-Process -Id $app.Id -Force }
        }
    }
    $uninstall = Start-Process (Join-Path $target 'unins000.exe') -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -PassThru
    if ($uninstall.ExitCode -ne 0) { throw "$name uninstall failed" }
    Write-Output "PASS: installed, opened and uninstalled $name"
}
