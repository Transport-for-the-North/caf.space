@echo off

REM Check if conda command is available
call conda -V
if errorlevel 1 (
    echo conda command cannot be found, this may be because it isn't installed or hasn't been added to path.
    echo conda can be installed using Miniforge3 from https://conda-forge.org/miniforge/
    goto end
)

set env_name=sat_itn_comp

echo ------------------------------------------------------------------------
echo Checking for environment with name %env_name%
echo ------------------------------------------------------------------------
call conda env list | find /i "%env_name%"

IF errorlevel 1 (
    echo ------------------------------------------------------------------------
    echo Creating %env_name%
    echo ------------------------------------------------------------------------
    call conda create -n %env_name% --file requirements.txt -y
)

echo ------------------------------------------------------------------------
echo Activating %env_name%
echo ------------------------------------------------------------------------
call conda activate %env_name%
echo Done

:end
call cmd /k

