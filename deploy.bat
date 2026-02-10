@echo off
echo ==========================================
echo      Market Radar - Smart Deploy
echo ==========================================

echo [1/4] Pulling latest changes from Cloud...
git pull origin main
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Pull failed! Please resolve conflicts manually.
    pause
    exit /b
)

echo [2/4] Staging changes...
git add .

set /p commit_msg="Enter commit message (Press Enter for 'Update'): "
if "%commit_msg%"=="" set commit_msg=Update

echo [3/4] Committing...
git commit -m "%commit_msg%"

echo [4/4] Pushing to Cloud...
git push origin main

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Push Failed! Please check the error message above.
    echo hint: You might need to run 'git pull' again.
    pause
    exit /b
)

echo.
echo ==========================================
echo  SUCCESS! Vercel is deploying your new version.
echo ==========================================
pause
