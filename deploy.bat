@echo off
echo ==========================================
echo      Market Radar - One-Click Deploy
echo ==========================================

echo [1/3] Staging changes...
git add .

set /p msg="Enter commit message (Press Enter for 'Update'): "
if "%msg%"=="" set msg=Update

echo [2/3] Committing...
git commit -m "%msg%"

echo [3/3] Pushing to Cloud...
git push

echo ==========================================
echo  SUCCESS! Vercel is deploying your new version.
echo ==========================================
pause
