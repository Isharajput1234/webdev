@echo off

cd /d "C:\Users\ishar\OneDrive\Documents\webdev"

:loop

git add .

git commit -m "Auto update"

git push origin main

timeout /t 60

goto loop