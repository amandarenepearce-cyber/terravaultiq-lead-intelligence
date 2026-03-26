TEREVAULTIQ UPGRADE

WHAT THIS VERSION DOES
- Google-based business discovery
- Missing website detection
- Weak website scoring
- Public email, phone, Facebook, and Instagram pull from websites
- CRM-style columns for outreach
- Upload and enrich your own CSV lists
- Lead Package Builder for internal or client delivery
- Search Planner for public intent, relocation, and community interest research
- TerevaultIQ branding throughout the app

FILES
- terevaultiq_upgrade.py
- requirements.txt
- START_TEREVAULTIQ_UPGRADE.bat

HOW TO RUN
1. Unzip this folder anywhere on your computer
2. Open Command Prompt in the unzipped folder
3. Install dependencies:
   pip install -r requirements.txt
4. Start the app:
   streamlit run terevaultiq_upgrade.py

WINDOWS QUICK START
- Double-click START_TEREVAULTIQ_UPGRADE.bat

NOTES
- You need your own Google API key for business discovery
- Website auditing works from public websites
- The Search Planner generates phrases; it does not scrape platforms directly
- This package is branded as TerevaultIQ Upgrade

GOOD FIRST TEST
- Lead type: roofers
- Search word: roofers
- City: Leavenworth, KS
- Radius: 25
