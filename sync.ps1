# Copies the game from the ManStudio folder into this project (code + music only; never saves, logs or account files).
# Run it after changing the game, then push: GitHub builds a new APK.
$ErrorActionPreference = 'Stop'
$src = Join-Path $env:USERPROFILE 'Desktop\ManStudio\ColorUnderPressure_VS_MSIX'
$dst = Join-Path $PSScriptRoot 'app'
Copy-Item (Join-Path $src 'color_rush.py') $dst -Force
Get-ChildItem $src -File | Where-Object { $_.Extension -in '.mp3', '.ogg' } | ForEach-Object { Copy-Item $_.FullName $dst -Force }
Copy-Item (Join-Path $src 'msix_layout\Assets\Square150x150Logo.png') (Join-Path $PSScriptRoot 'icon.png') -Force
Copy-Item (Join-Path $src 'msix_layout\Assets\SplashScreen.png') (Join-Path $PSScriptRoot 'presplash.png') -Force
Write-Output "synced: color_rush.py + music"
