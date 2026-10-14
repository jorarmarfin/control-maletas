# Genera dist\ControlMaletas-<ver>.msix a partir de dist\ControlMaletas\ (onedir de PyInstaller).
# Firma con certificado autofirmado (para pruebas) o con el .pfx indicado por variables:
#   $env:MSIX_PFX_PATH / $env:MSIX_PFX_PASSWORD  (certificado real, opcional)
param([string]$Version = "0.1.0")
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

$parts = $Version.Split(".")
while ($parts.Count -lt 4) { $parts += "0" }
$msixVersion = ($parts[0..3] -join ".")

function Find-SdkTool($name) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $hit = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\$name" -ErrorAction SilentlyContinue |
         Sort-Object FullName -Descending | Select-Object -First 1
  if (-not $hit) { throw "No se encontró $name (instale el Windows SDK)." }
  return $hit.FullName
}
$makeappx = Find-SdkTool "makeappx.exe"
$signtool = Find-SdkTool "signtool.exe"

$stage = Join-Path $root "build\msix"
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item "dist\ControlMaletas\*" $stage -Recurse
python packaging\msix\make_assets.py assets\logo.png (Join-Path $stage "Assets")

# Certificado
$subject = "CN=ControlMaletas"
if ($env:MSIX_PFX_PATH) {
  $pfx = $env:MSIX_PFX_PATH; $pwd = $env:MSIX_PFX_PASSWORD
  $subject = (New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 $pfx, $pwd).Subject
} else {
  $cert = New-SelfSignedCertificate -Type Custom -Subject $subject -KeyUsage DigitalSignature `
    -FriendlyName "Control Maletas (prueba)" -CertStoreLocation "Cert:\CurrentUser\My" `
    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
  $pwd = "ControlMaletas-test"
  $pfx = Join-Path $root "build\ControlMaletas-test.pfx"
  Export-PfxCertificate -Cert $cert -FilePath $pfx -Password (ConvertTo-SecureString $pwd -AsPlainText -Force) | Out-Null
  Export-Certificate -Cert $cert -FilePath (Join-Path $root "dist\ControlMaletas-test.cer") | Out-Null
}

(Get-Content "packaging\msix\AppxManifest.template.xml" -Raw) `
  -replace "__PUBLISHER__", $subject -replace "__VERSION__", $msixVersion |
  Set-Content (Join-Path $stage "AppxManifest.xml") -Encoding UTF8

$out = Join-Path $root "dist\ControlMaletas-$Version.msix"
& $makeappx pack /d $stage /p $out /o
& $signtool sign /fd SHA256 /f $pfx /p $pwd $out
Write-Host "MSIX generado: $out"
