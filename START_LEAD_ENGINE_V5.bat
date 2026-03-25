@echo off
title Lead Engine V5
echo Starting Lead Engine V5...
py -m pip install -r requirements_v5.txt
py -m streamlit run lead_engine_v5.py
pause
