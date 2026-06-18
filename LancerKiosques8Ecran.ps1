# LancerKiosques_FINAL_8_Ecrans.ps1
# - Ajout du 2e NSOC sur X=7680 Y=1080
# - Flow maintenu sur X=3840 Y=0
# - Profils Persistants + Dark Mode + URLs Fixes

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinAPI {
 [DllImport("user32.dll")]
 public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
 [DllImport("user32.dll")]
 public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

Add-Type -AssemblyName System.Windows.Forms
$allScreens = [System.Windows.Forms.Screen]::AllScreens

# ==============================================================================
# CONFIGURATION COMPLETE (8 ecrans)
# ==============================================================================
$liens = @(
 # 1. NSOC PRINCIPAL
 @{ profile='nsoc'; targetX=9600; targetY=1074; zoom=1; darkMode=$true; url='https://sublimeriad.github.io/retail-media/nsoc-status.html' },

 # 2. VNNOX
 @{ profile='vnnox'; targetX=9600; targetY=-6; zoom=1; darkMode=$true; url='https://eu.vnnox.com/care/#/dashboard' },

 # 3. IOT
 @{ profile='iot-admin'; targetX=7680; targetY=0; zoom=1; darkMode=$true; url='https://sublimeriad.github.io/retail-media/wall-dashboard.html' },

 # 4. NOUVEAU NSOC SECONDAIRE (Display 2 - Ancien emplacement de Flow)
 @{ profile='nsoc2'; targetX=7680; targetY=1080; zoom=1; darkMode=$true; url='https://sublimeriad.github.io/retail-media/grafana-dashboards/nsoc-black-screen.html' },

 # 5. FLOW (Nouvel emplacement)
 @{ profile='flow'; targetX=3840; targetY=0; zoom=1; darkMode=$true; url='https://adlivecenter.adlive.io/en/admin'; },

 # 6. ADS 1
 @{profile='ads'; targetX=5760; targetY=0; zoom=1; darkMode=$true; url='https://sublimeriad.github.io/retail-media/retailmedia.html' },

 # 7. ADS 2
 @{profile='ads2'; targetX=5760; targetY=1080; zoom=1; darkMode=$true; url='https://sublimeriad.github.io/retail-media/Retail-Media-Nsoc-Players.html' },

 # 8. ADS 3
 @{profile='ads3'; targetX=3840; targetY=1080; zoom=0.75; darkMode=$true; url='file:///C:/Users/User/Documents/ads3.html' }
)
# ==============================================================================

$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$altChromePath = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
$basePort = 9222
$rootProfileDir = "C:\KiosqueData"

# --- Verifier Chrome ---
$chromeExe = $null
if (Test-Path $chromePath) { $chromeExe = $chromePath }
elseif (Test-Path $altChromePath) { $chromeExe = $altChromePath }
else {
    Write-Host "ERREUR : Chrome introuvable !"
    Write-Host "  Verifie : $chromePath"
    Write-Host "  Verifie : $altChromePath"
    exit 1
}

if (-not (Test-Path $rootProfileDir)) { New-Item -ItemType Directory -Path $rootProfileDir | Out-Null }

Write-Host "Fermeture des processus Chrome kiosques uniquement..."
# Tue uniquement les Chrome lances depuis ce script (en tuant les ports de debogage connus)
for ($i = 0; $i -lt $liens.Count; $i++) {
    $port = $basePort + $i
    $proc = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($proc) {
        Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 2

Write-Host "=== Demarrage Kiosques (8 ecrans) ==="

for ($i = 0; $i -lt $liens.Count; $i++) {
    $link = $liens[$i]
    $tX = $link.targetX
    $tY = $link.targetY

    # Trouver l'ecran
    $targetScreen = $allScreens | Where-Object {
        ([math]::Abs($_.Bounds.X - $tX) -le 50) -and
        ([math]::Abs($_.Bounds.Y - $tY) -le 50)
    } | Select-Object -First 1

    if ($null -eq $targetScreen) {
        Write-Warning ">> ERREUR : Ecran introuvable X=$tX / Y=$tY pour $($link.profile). Verifie la config ecran."
        continue
    }

    Write-Host "[$($i+1)/$($liens.Count)] '$($link.profile)' -> X=$tX, Y=$tY"

    # Gestion du profil persistant
    $userDataDir = Join-Path $rootProfileDir $link.profile
    if (-not (Test-Path $userDataDir)) { New-Item -ItemType Directory -Path $userDataDir | Out-Null }

    $port = $basePort + $i

    $args = @(
        "--new-window",
        "--user-data-dir=$userDataDir",
        "--kiosk",
        "--force-device-scale-factor=$($link.zoom)",
        "--no-first-run",
        "--no-default-browser-check",
        "--enable-features=WebContentsForceDark",
        "--disable-translate",
        "--remote-debugging-port=$port",
        "--window-position=$($targetScreen.Bounds.X),$($targetScreen.Bounds.Y)",
        "--window-size=$($targetScreen.Bounds.Width),$($targetScreen.Bounds.Height)"
    )

    if ($link.darkMode -eq $true) {
        $args += "--force-dark-mode"
    }

    $args += $link.url

    $proc = Start-Process -FilePath $chromeExe -ArgumentList $args -PassThru -WindowStyle Maximized

    # Attente du handle fenetre
    $hwnd = $null
    for ($j = 0; $j -lt 40; $j++) {
        Start-Sleep -Milliseconds 250
        try {
            $proc.Refresh()
            $hwnd = $proc.MainWindowHandle
            if ($hwnd -ne 0 -and $hwnd -ne -1) { break }
        }
        catch {
            # Processus deja termine
            $hwnd = 0
        }
    }

    if ($hwnd -ne 0 -and $hwnd -ne -1) {
        [WinAPI]::MoveWindow($hwnd, $targetScreen.Bounds.X, $targetScreen.Bounds.Y, $targetScreen.Bounds.Width, $targetScreen.Bounds.Height, $true)
        [WinAPI]::ShowWindow($hwnd, 3)
        Start-Sleep -Milliseconds 1000
        [WinAPI]::MoveWindow($hwnd, $targetScreen.Bounds.X, $targetScreen.Bounds.Y, $targetScreen.Bounds.Width, $targetScreen.Bounds.Height, $true)
        Write-Host "  -> OK (handle=0x$('{0:X}' -f $hwnd))"
    }
    else {
        Write-Warning "  -> ERREUR : handle fenetre introuvable pour $($link.profile)"
    }
}

Write-Host "`nTermine. Les 8 ecrans sont en kiosque."
