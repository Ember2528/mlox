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





rem Update mlox-rules
echo Updating mlox-rules ...

rem create ./mlox/ directory
if not exist mlox\NUL mkdir mlox

rem check if ./mlox/ is a git repository
if exist mlox/.git goto ISGIT else goto ISNOTGIT

:ISNOTGIT
rem Clone just the repository's .git folder excluding files as they are already in `mlox` into an empty temporary directory
rem see https://stackoverflow.com/a/2484349/16407587
git clone --no-checkout https://github.com/DanaePlays/mlox-rules.git mlox/mlox.tmp 

rem Move the .git folder to the directory with the files.
rem This makes `mlox` a git repo.
robocopy mlox/mlox.tmp mlox /E /MOVE /NFL /NDL

rem git thinks all files are deleted, this reverts the state of the repo to HEAD.
rem WARNING: any local changes to the files will be lost.
cd mlox
git reset --hard HEAD
cd ..

:ISGIT
rem fetch and fast-forward pull mlox-rules
cd mlox
git fetch
git pull --ff-only

pause
