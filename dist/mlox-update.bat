@echo off

rem Update mlox.exe
echo Updating mlox.exe ...

rem check installed version
if exist mlox.manifest (goto :EXISTING) else goto :MISSING

:EXISTING
rem read version from manifest
set /p cmanifest=<mlox.manifest
set curversion=%cmanifest:~84,5%
goto :FINALLY

:MISSING
set curversion=NULL

:FINALLY
echo installed: "%curversion%"

rem check available version
rem always download the current manifest
curl https://github.com/rfuzzo/mlox/releases/latest/download/mlox.exe -o mlox.manifest

set /p manifest=<mlox.manifest
set version=%manifest:~84,5%
echo available: "%version%"

rem compare versions
if "%curversion%"=="%version%" (
    rem already installed
    echo Latest version installed
) else (
    rem download the actual file
    echo Downloading mlox.exe ...
	curl -L https://github.com/rfuzzo/mlox/releases/latest/download/mlox.exe -o mlox.exe
)

pause
