@echo off

cd /d "C:\Users\ishar\OneDrive\Documents\webdev"

:loop

git add .

git diff --cached --quiet
if %errorlevel%==0 goto skip

git commit -m "Auto update"
git push origin main

:skip

timeout /t 60

goto loop