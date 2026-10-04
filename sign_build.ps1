#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Self-Signed Code Signing Certificate generator and EXE signer for
    "Floating Sinhala Translator".

.DESCRIPTION
    1. Creates a SHA-256 / RSA-4096 self-signed code signing certificate
       (valid 5 years) in the CurrentUser\My certificate store.
    2. Exports it as a .pfx (password-protected private key) and a .cer
       (public key only -- safe to share / deploy).
    3. Installs the .cer into both TrustedPublisher and Root stores so that
       Windows SmartScreen and UAC trust the EXE on this machine.
    4. Signs the compiled EXE.
         Primary path   : signtool.exe (Windows SDK / VS Build Tools)
         Automatic fallback: Set-AuthenticodeSignature (built-in PowerShell
                            cmdlet -- no SDK required, RFC 3161 timestamp
                            added via the TimestampServer parameter).
    5. Verifies the signature.

.NOTES
    Run this script AFTER pyinstaller has produced dist\translator.exe
    (or the equivalent from the COLLECT spec).

    Requires:
      - Administrator rights (needed to write to the Root cert store).
      - signtool.exe is OPTIONAL -- the script falls back to PowerShell's
        native Set-AuthenticodeSignature if the Windows SDK is not installed.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# CONFIGURATION -- change these to match your setup
# ---------------------------------------------------------------------------
$CertSubject      = 'CN=Floating Sinhala Translator, O=NimanthaShyamin, C=LK'
$CertFriendlyName = 'Floating Sinhala Translator Self-Signed'
$CertValidYears   = 5
# $ExePath is resolved automatically below -- see Step 5b.
$CerExportPath    = Join-Path $PSScriptRoot 'FloatingSinhalaTranslator_CodeSign.cer'
$PfxExportPath    = Join-Path $PSScriptRoot 'FloatingSinhalaTranslator_CodeSign.pfx'
$TimestampUrl     = 'http://timestamp.digicert.com'   # Free RFC 3161 TSA
# ---------------------------------------------------------------------------

function Write-Step($msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# Step 1 -- Create the self-signed certificate
# ---------------------------------------------------------------------------
Write-Step 'Creating self-signed code signing certificate ...'

$expiry = (Get-Date).AddYears($CertValidYears)

$cert = New-SelfSignedCertificate `
    -Subject           $CertSubject `
    -FriendlyName      $CertFriendlyName `
    -CertStoreLocation 'Cert:\CurrentUser\My' `
    -KeyAlgorithm      RSA `
    -KeyLength         4096 `
    -HashAlgorithm     SHA256 `
    -KeyUsage          DigitalSignature `
    -Type              CodeSigningCert `
    -NotAfter          $expiry

Write-Host "Certificate thumbprint: $($cert.Thumbprint)" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Step 2 -- Export .pfx (private key, password-protected)
# ---------------------------------------------------------------------------
Write-Step 'Exporting .pfx (private key) ...'
$pfxPassword = Read-Host -Prompt 'Enter a password to protect the .pfx file' -AsSecureString
Export-PfxCertificate -Cert $cert -FilePath $PfxExportPath -Password $pfxPassword | Out-Null
Write-Host "PFX saved to: $PfxExportPath" -ForegroundColor Green
Write-Host '*** Keep this file PRIVATE -- it contains your signing private key. ***' -ForegroundColor Yellow

# ---------------------------------------------------------------------------
# Step 3 -- Export .cer (public key only -- safe to share)
# ---------------------------------------------------------------------------
Write-Step 'Exporting .cer (public key, safe to share) ...'
Export-Certificate -Cert $cert -FilePath $CerExportPath -Type CERT | Out-Null
Write-Host "CER saved to: $CerExportPath" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Step 4 -- Install .cer into TrustedPublisher and Root stores (this machine)
# ---------------------------------------------------------------------------
Write-Step 'Installing certificate into TrustedPublisher and Root stores ...'

$storeTP = New-Object System.Security.Cryptography.X509Certificates.X509Store(
    [System.Security.Cryptography.X509Certificates.StoreName]::TrustedPublisher,
    [System.Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine
)
$storeTP.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
$storeTP.Add($cert)
$storeTP.Close()

$storeRoot = New-Object System.Security.Cryptography.X509Certificates.X509Store(
    [System.Security.Cryptography.X509Certificates.StoreName]::Root,
    [System.Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine
)
$storeRoot.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
$storeRoot.Add($cert)
$storeRoot.Close()

Write-Host 'Certificate installed in LocalMachine\TrustedPublisher and LocalMachine\Root.' -ForegroundColor Green

# ---------------------------------------------------------------------------
# Step 5 -- Locate signtool.exe (optional -- we fall back gracefully)
# ---------------------------------------------------------------------------
Write-Step 'Locating signtool.exe (optional) ...'

$sdkRoots = @(
    'C:\Program Files (x86)\Windows Kits\10\bin',
    'C:\Program Files\Windows Kits\10\bin'
)

$signtool = $null
foreach ($root in $sdkRoots) {
    if (Test-Path $root) {
        $signtool = Get-ChildItem -Path $root -Recurse -Filter 'signtool.exe' -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match 'x64' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1 -ExpandProperty FullName
        if ($signtool) { break }
    }
}

if ($signtool) {
    Write-Host "signtool.exe found: $signtool" -ForegroundColor Green
} else {
    Write-Host 'signtool.exe NOT found -- will use Set-AuthenticodeSignature fallback.' -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Step 5b -- Auto-detect the built EXE under dist\
# ---------------------------------------------------------------------------
Write-Step 'Auto-detecting built EXE under dist\ ...'

# Priority order:
#  1. COLLECT layout  (Floating Sinhala Translator.spec)
#  2. One-file layout (translator.spec)
#  3. Any other *.exe found recursively under dist\
$candidatePaths = @(
    (Join-Path $PSScriptRoot 'dist\Floating Sinhala Translator\Floating Sinhala Translator.exe'),
    (Join-Path $PSScriptRoot 'dist\translator.exe')
)

$ExePath = $null
foreach ($candidate in $candidatePaths) {
    if (Test-Path $candidate) {
        $ExePath = $candidate
        break
    }
}

if (-not $ExePath) {
    Write-Host 'Known paths not found -- scanning dist\ recursively for any .exe ...' -ForegroundColor Yellow
    $found = Get-ChildItem -Path (Join-Path $PSScriptRoot 'dist') -Recurse -Filter '*.exe' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($found) {
        $ExePath = $found.FullName
        Write-Host "Found by scan: $ExePath" -ForegroundColor Yellow
    }
}

if (-not $ExePath) {
    Write-Error "No EXE found under dist\.`nBuild the project first:`n  pyinstaller 'Floating Sinhala Translator.spec'`n  -- or --`n  pyinstaller translator.spec"
}

Write-Host "Target EXE: $ExePath" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Step 6 -- Sign the EXE  (signtool primary / Set-AuthenticodeSignature fallback)
# ---------------------------------------------------------------------------
Write-Step "Signing: $ExePath"

if ($signtool) {
    # ---- PRIMARY: signtool.exe ----
    Write-Host 'Using signtool.exe ...' -ForegroundColor DarkCyan

    & $signtool sign `
        /sha1 $cert.Thumbprint `
        /fd   SHA256 `
        /tr   $TimestampUrl `
        /td   SHA256 `
        /v    $ExePath

    if ($LASTEXITCODE -ne 0) {
        Write-Error "signtool sign failed (exit $LASTEXITCODE). See output above."
    }
    Write-Host 'EXE signed with signtool.exe.' -ForegroundColor Green

} else {
    # ---- FALLBACK: Set-AuthenticodeSignature (built-in, no SDK needed) ----
    Write-Host 'Using Set-AuthenticodeSignature (PowerShell native fallback) ...' -ForegroundColor DarkCyan

    # Re-open the certificate from CurrentUser\My using the thumbprint so the
    # private key is accessible to the signing cmdlet.
    $signingCert = Get-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)"

    $authSig = Set-AuthenticodeSignature `
        -FilePath        $ExePath `
        -Certificate     $signingCert `
        -HashAlgorithm   SHA256 `
        -TimestampServer $TimestampUrl

    if ($authSig.Status -notin @('Valid', 'UnknownError')) {
        # 'UnknownError' is returned when the cert chain is self-signed but the
        # signature itself was written successfully -- treat it as a soft warning.
        Write-Error "Set-AuthenticodeSignature failed. Status: $($authSig.Status)  StatusMessage: $($authSig.StatusMessage)"
    }

    Write-Host "EXE signed with Set-AuthenticodeSignature. Status: $($authSig.Status)" -ForegroundColor Green

    if ($authSig.Status -eq 'UnknownError') {
        Write-Host @'

  NOTE: Status "UnknownError" is normal for self-signed certificates -- it
  means the signature was embedded successfully but the cert chain cannot be
  verified against a public root CA.  The EXE IS signed; machines that have
  your .cer installed in TrustedRoot + TrustedPublisher will trust it fully.
'@ -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# Step 7 -- Verify the signature
# ---------------------------------------------------------------------------
Write-Step 'Verifying signature ...'

if ($signtool) {
    # signtool verify is stricter -- use it when available
    & $signtool verify /pa /v $ExePath
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "signtool verify returned exit $LASTEXITCODE -- expected for self-signed certs before the .cer is installed in the Root store."
    } else {
        Write-Host 'Signature verified by signtool.exe.' -ForegroundColor Green
    }
} else {
    # PowerShell-native verification
    $verifyResult = Get-AuthenticodeSignature -FilePath $ExePath
    Write-Host "Authenticode status : $($verifyResult.Status)" -ForegroundColor Cyan
    Write-Host "Signer certificate  : $($verifyResult.SignerCertificate.Subject)" -ForegroundColor Cyan

    if ($verifyResult.Status -in @('Valid', 'UnknownError')) {
        Write-Host 'Signature is present and readable (self-signed -- install .cer to make it fully trusted).' -ForegroundColor Green
    } else {
        Write-Warning "Unexpected status: $($verifyResult.Status) -- $($verifyResult.StatusMessage)"
    }
}

# ---------------------------------------------------------------------------
# Done -- print deployment instructions
# ---------------------------------------------------------------------------
Write-Host @'

=============================================================================
 DONE!  Summary of generated files
=============================================================================

  FloatingSinhalaTranslator_CodeSign.pfx  -- Private signing key (KEEP SECRET)
  FloatingSinhalaTranslator_CodeSign.cer  -- Public certificate (safe to share)

-----------------------------------------------------------------------------
 HOW TO INSTALL THE CERTIFICATE ON THIS MACHINE (already done by this script)
-----------------------------------------------------------------------------
  The .cer has been added to:
    LocalMachine\TrustedPublisher  -- suppresses "Unknown Publisher" UAC prompt
    LocalMachine\Root              -- makes the cert chain valid / trusted

-----------------------------------------------------------------------------
 HOW TO TRUST THE EXE ON ANOTHER MACHINE (end-user or team member)
-----------------------------------------------------------------------------
  1. Copy FloatingSinhalaTranslator_CodeSign.cer to the target PC.
  2. Open an ELEVATED PowerShell on that PC and run:

       $cer = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("C:\path\to\FloatingSinhalaTranslator_CodeSign.cer")

       $tp = New-Object System.Security.Cryptography.X509Certificates.X509Store("TrustedPublisher","LocalMachine")
       $tp.Open("ReadWrite"); $tp.Add($cer); $tp.Close()

       $rt = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root","LocalMachine")
       $rt.Open("ReadWrite"); $rt.Add($cer); $rt.Close()

  OR via MMC (GUI):
    Win+R -> mmc -> File -> Add/Remove Snap-in -> Certificates (Computer account)
    -> expand "Trusted Root Certification Authorities" -> right-click Certificates
    -> All Tasks -> Import -> select the .cer file -> repeat for
    "Trusted Publishers".

-----------------------------------------------------------------------------
 SmartScreen / Smart App Control notes
-----------------------------------------------------------------------------
  Self-signed certs suppress the warning ONLY on machines where the .cer has
  been imported.  For public internet distribution without requiring users to
  install a certificate, you need a commercially purchased Authenticode or EV
  Code Signing certificate.  EV certificates bypass SmartScreen reputation
  checks immediately (no download count threshold required).

  Reputable vendors (no endorsement implied):
    https://www.digicert.com/signing/code-signing-certificates
    https://www.sectigo.com/ssl-certificates-tls/code-signing
    https://www.ssl.com/certificates/ev-code-signing/

-----------------------------------------------------------------------------
 Renewing the certificate (before 5-year expiry)
-----------------------------------------------------------------------------
  Simply re-run this script.  It will create a new thumbprint, re-sign your
  new build, and install the updated cert on this machine.

=============================================================================
'@ -ForegroundColor White
