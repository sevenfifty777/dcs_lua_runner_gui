[CmdletBinding()]
param(
    [ValidatePattern('^\d+\.\d+(?:\.\d+)?(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Version = '2.0'
)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$distributionName = "DCS_Lua_Runner_GUI_v$Version"
$distributionPath = [IO.Path]::GetFullPath((Join-Path $projectRoot $distributionName))

if ([IO.Path]::GetDirectoryName($distributionPath) -ne $projectRoot) {
    throw 'Refusing to create a distribution outside the repository root.'
}

Push-Location $projectRoot
try {
    $pyinstallerVersion = (& pyinstaller --version).Trim()
    if ($LASTEXITCODE -ne 0 -or $pyinstallerVersion -ne '6.22.2') {
        throw "PyInstaller 6.22.2 is required; found '$pyinstallerVersion'."
    }

    & pyinstaller build_exe.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    if (Test-Path -LiteralPath $distributionPath) {
        Remove-Item -LiteralPath $distributionPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $distributionPath | Out-Null

    $files = @(
        'dist\DCS_Lua_Runner_GUI.exe',
        'README.md',
        'QUICK_START.md',
        'LICENSE',
        'dcs-fiddle-server.lua',
        'dcs-fiddle-config.lua.example',
        'dcs_lua_runner_settings.json.tpl'
    )
    foreach ($file in $files) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Required distribution file is missing: $file"
        }
        Copy-Item -LiteralPath $file -Destination $distributionPath
    }

    Copy-Item -LiteralPath 'deploy' -Destination $distributionPath -Recurse
    Copy-Item -LiteralPath 'docs' -Destination $distributionPath -Recurse

    $packagedLua = Join-Path $distributionPath 'dcs-fiddle-server.lua'
    $rootHash = (Get-FileHash -Algorithm SHA256 -LiteralPath 'dcs-fiddle-server.lua').Hash
    $packagedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $packagedLua).Hash
    if ($rootHash -ne $packagedHash) {
        throw 'Packaged Lua hash does not match the validated root Lua file.'
    }

    $forbiddenNames = @('dcs-fiddle-config.lua', 'dcs_lua_runner_settings.json', '.env')
    $forbiddenFiles = Get-ChildItem -LiteralPath $distributionPath -Recurse -File |
        Where-Object Name -In $forbiddenNames
    if ($forbiddenFiles) {
        throw "Distribution contains a forbidden runtime configuration file: $($forbiddenFiles.FullName -join ', ')"
    }

    $secretCandidates = Get-ChildItem -LiteralPath $distributionPath -Recurse -File |
        Where-Object Extension -In '.lua', '.json', '.pem', '.key'
    $secretMatches = $secretCandidates | Select-String -Pattern 'BEGIN (?:RSA |EC )?PRIVATE KEY|web_auth_password'
    if ($secretMatches) {
        throw 'Distribution secret scan found a private-key marker or legacy password field.'
    }

    $executable = Join-Path $distributionPath 'DCS_Lua_Runner_GUI.exe'
    $smokeTest = Start-Process -FilePath $executable -ArgumentList '--version' -Wait -PassThru -WindowStyle Hidden
    if ($smokeTest.ExitCode -ne 0) {
        throw "Packaged executable smoke test failed with exit code $($smokeTest.ExitCode)."
    }

    $executableHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $executable).Hash
    Write-Host "Created $distributionPath"
    Write-Host "Lua SHA-256: $rootHash"
    Write-Host "Executable SHA-256: $executableHash"
}
finally {
    Pop-Location
}
