Unicode true
Name "Link Guard"
OutFile "..\..\dist\LinkGuard-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\LinkGuard"
RequestExecutionLevel user
SetCompressor /SOLID lzma

!define UNINST "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkGuard"
!define RUNKEY "Software\Microsoft\Windows\CurrentVersion\Run"

Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Section "Install"
  IfFileExists "$INSTDIR\LinkGuard.exe" 0 +3
    nsExec::Exec '"$INSTDIR\LinkGuard.exe" --quit'
    Sleep 1500
  SetOutPath "$INSTDIR"
  File "..\..\dist\LinkGuard.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\Link Guard"
  CreateShortcut "$SMPROGRAMS\Link Guard\Link Guard.lnk" "$INSTDIR\LinkGuard.exe"
  CreateShortcut "$SMPROGRAMS\Link Guard\Uninstall Link Guard.lnk" "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "${UNINST}" "DisplayName" "Link Guard"
  WriteRegStr HKCU "${UNINST}" "DisplayIcon" "$INSTDIR\LinkGuard.exe"
  WriteRegStr HKCU "${UNINST}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINST}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "${UNINST}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKCU "${UNINST}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST}" "NoRepair" 1

  WriteRegStr HKCU "${RUNKEY}" "LinkGuard" '"$INSTDIR\LinkGuard.exe" --background'
SectionEnd

Function .onInstSuccess
  Exec '"$INSTDIR\LinkGuard.exe"'
FunctionEnd

Section "Uninstall"
  nsExec::Exec '"$INSTDIR\LinkGuard.exe" --quit'
  Sleep 1500
  Delete "$INSTDIR\LinkGuard.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  Delete "$SMPROGRAMS\Link Guard\Link Guard.lnk"
  Delete "$SMPROGRAMS\Link Guard\Uninstall Link Guard.lnk"
  RMDir "$SMPROGRAMS\Link Guard"
  DeleteRegKey HKCU "${UNINST}"
  DeleteRegValue HKCU "${RUNKEY}" "LinkGuard"
SectionEnd
