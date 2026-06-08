# Charles Discord Join Scraper

Self-bot join tracker for **charlesmark333** — forwards captures to **Charles Auto wise** group DM.

## Local run

```powershell
cd C:\Users\HP\Downloads\scraper-charles
pip install -r requirements.txt
python bot.py
```

Copy `.env.example` to `.env` and set `USER_TOKEN` if needed. Run **one** instance per token (local **or** Render).

## GitHub + Render (when ready)

Create repo `scraper-charles` on GitHub, then:

```powershell
cd C:\Users\HP\Downloads\scraper-charles
git init
git add bot.py requirements.txt README.md .env.example .gitignore render.yaml runtime.txt
git commit -m "Charles join tracker"
git branch -M main
git remote add origin https://github.com/okwujiaku/scraper-charles.git
git push -u origin main
```

Never commit `.env`. On Render: Background Worker, add `USER_TOKEN`, `PYTHON_VERSION=3.11.9`.

Self-botting violates Discord ToS; use at your own risk.
