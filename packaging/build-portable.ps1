# Construye el paquete Windows con dependencias fijadas, desde cualquier carpeta.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$buildPython = Join-Path $projectRoot '.venv-build\Scripts\python.exe'
$originalPath = $env:PATH
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath $buildPython)) {
        py -3.14 -m venv .venv-build
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno de build' }
    }
    & $buildPython -m pip install -r packaging/requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación de dependencias' }
    & $buildPython packaging/prepare_assets.py
    if ($LASTEXITCODE -ne 0) { throw 'Falló la preparación de recursos' }
    # Evita incorporar DLLs homónimas de otras herramientas presentes en PATH.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    & $buildPython -m PyInstaller --clean --noconfirm --distpath dist --workpath build/pyinstaller 'packaging/Mouse for Fools.spec'
    if ($LASTEXITCODE -ne 0) { throw 'Falló PyInstaller' }
    $bundle = Join-Path $projectRoot 'dist\Mouse for Fools'
    Copy-Item -LiteralPath 'LICENSE' -Destination $bundle
    Copy-Item -LiteralPath 'packaging/LEEME.txt' -Destination $bundle
    Copy-Item -LiteralPath 'packaging/THIRD-PARTY-NOTICES.md' -Destination $bundle
    Copy-Item -LiteralPath 'packaging/VALIDACION.md' -Destination $bundle
    Copy-Item -Path 'src/mouse_for_fools/legal/*.md' -Destination $bundle
    Copy-Item -LiteralPath 'build/licenses' -Destination $bundle -Recurse -Force
    $zip = Join-Path $projectRoot 'dist\Mouse-for-Fools-fase4-win64.zip'
    Compress-Archive -LiteralPath $bundle -DestinationPath $zip -Force
    Get-FileHash -LiteralPath $zip -Algorithm SHA256
} finally {
    $env:PATH = $originalPath
    Pop-Location
}
