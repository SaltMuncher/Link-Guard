Unicode true
Name "Link Guard"
OutFile "..\..\dist\LinkGuard-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\LinkGuard"
RequestExecutionLevel user
SetCompressor /SOLID lzma

!define UNINST "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkGuard"
!define RUNKEY "Software\Microsoft\Windows\CurrentVersion\Run"

Var RemoveOld

Function .onInit
  StrCpy $RemoveOld 0
  IfFileExists "$LOCALAPPDATA\Programs\LinkGuard\LinkGuard.exe" 0 oldDone
  MessageBox MB_YESNO|MB_ICONQUESTION "An older version of Link Guard was found in:$\r$\n$LOCALAPPDATA\Programs\LinkGuard$\r$\n$\r$\nDelete it and install the new version?" /SD IDYES IDYES oldRemove
  Abort
oldRemove:
  StrCpy $RemoveOld 1
oldDone:
FunctionEnd

Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Section "Install"
  StrCmp $RemoveOld 1 0 skipRemove
  nsExec::Exec '"$LOCALAPPDATA\Programs\LinkGuard\LinkGuard.exe" --quit'
  Sleep 1500
  Delete "$LOCALAPPDATA\Programs\LinkGuard\LinkGuard.exe"
  Delete "$LOCALAPPDATA\Programs\LinkGuard\Uninstall.exe"
  RMDir "$LOCALAPPDATA\Programs\LinkGuard"
  Delete "$SMPROGRAMS\Link Guard\Link Guard.lnk"
  Delete "$SMPROGRAMS\Link Guard\Uninstall Link Guard.lnk"
  RMDir "$SMPROGRAMS\Link Guard"
  DeleteRegKey HKCU "${UNINST}"
  DeleteRegValue HKCU "${RUNKEY}" "LinkGuard"
skipRemove:
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
