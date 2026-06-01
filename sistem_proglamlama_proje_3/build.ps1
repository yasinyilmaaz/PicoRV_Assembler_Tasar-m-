# =====================================================================
# RISC-V Toolchain Build & Assemble Script
# =====================================================================
# Kullanım:
#   .\build.ps1 -Tool                 # assembler/linker C kodunu derle
#   .\build.ps1 -Asm asm\led.asm      # tek dosyayı assemble + link et
#   .\build.ps1 -All                  # asm/ klasöründeki her şeyi link et
#   .\build.ps1 -Clean                # build/ klasörünü temizle
# =====================================================================

param(
    [switch]$Tool,
    [string]$Asm = "",
    [switch]$All,
    [switch]$Clean,
    [string]$Ttext = "0x0",
    [string]$Tdata = "0x1000"
)

$Root = $PSScriptRoot
$Bin  = Join-Path $Root "toolchain\bin"
$Src  = Join-Path $Root "toolchain\src"
$Build= Join-Path $Root "build"
$AsmD = Join-Path $Root "asm"

function Build-Toolchain {
    Write-Host "[i] Toolchain derleniyor..." -ForegroundColor Cyan
    Push-Location $Src
    gcc assembler.c -o (Join-Path $Bin "assembler.exe")
    gcc linker.c    -o (Join-Path $Bin "linker.exe")
    Pop-Location
    # Mark-of-the-Web / SmartScreen engelini kaldir (her yeniden derlemede gerekir)
    Get-ChildItem -Path $Bin -Filter *.exe -ErrorAction SilentlyContinue | ForEach-Object {
        try { Unblock-File -Path $_.FullName -ErrorAction Stop } catch {}
    }
    Write-Host "[+] OK: $Bin\assembler.exe , linker.exe (unblocked)" -ForegroundColor Green
}

function Build-One($asmFile) {
    if (-not (Test-Path $asmFile)) { Write-Host "[X] Dosya yok: $asmFile" -ForegroundColor Red; return }
    $name = [IO.Path]::GetFileNameWithoutExtension($asmFile)
    $obj  = Join-Path $Build "$name.o"
    $mem  = Join-Path $Build "$name.mem"
    Write-Host "[>] $name.asm  ->  $name.o  ->  $name.mem" -ForegroundColor Yellow
    & (Join-Path $Bin "assembler.exe") $asmFile $obj
    if ($?) {
        & (Join-Path $Bin "linker.exe") -Ttext $Ttext -Tdata $Tdata -o $mem $obj
    }
}

if ($Clean) {
    Remove-Item "$Build\*" -Force -ErrorAction SilentlyContinue
    Write-Host "[+] build/ temizlendi." -ForegroundColor Green
    return
}

if ($Tool) { Build-Toolchain; return }

if (-not (Test-Path $Build)) { New-Item -ItemType Directory -Path $Build | Out-Null }

if ($Asm) { Build-One $Asm; return }

if ($All) {
    Get-ChildItem $AsmD -Filter *.asm | ForEach-Object { Build-One $_.FullName }
    # tests/ klasöründeki dosyaları da işle
    $TestsD = Join-Path (Split-Path $Root -Parent) "tests"
    if (Test-Path $TestsD) {
        Get-ChildItem $TestsD -Filter *.asm | ForEach-Object { Build-One $_.FullName }
    }
    return
}

Write-Host @"
Kullanim:
  .\build.ps1 -Tool                # assembler/linker derle
  .\build.ps1 -Asm asm\led.asm     # tek dosyayi build et
  .\build.ps1 -All                 # asm\ + ..\tests\ butun .asm'leri
  .\build.ps1 -Clean               # build\ temizle
Opsiyon:
  -Ttext 0x0  -Tdata 0x1000        # ozel adresler
"@ -ForegroundColor Gray
