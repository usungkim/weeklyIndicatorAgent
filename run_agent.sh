#!/bin/bash
cd "/Users/woosungkim/Desktop/Weekly Indicator Agent"
source venv/bin/activate
echo "" >> agent.log
echo "==================== $(date '+%Y-%m-%d %H:%M:%S') ====================" >> agent.log
python3 main.py >> agent.log 2>&1