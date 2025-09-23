# ENCAR Parser & Landing 🚗

Daily updated scraper and responsive landing page for used cars from [Encar.com](https://www.encar.com).  
The project collects **brand, model, year, mileage, price, and photo** of cars and publishes them as a simple adaptive landing page.

---

## 🔗 Live Demo
👉 [View site on GitHub Pages](https://OfUndefiend.github.io/encar-parser-landing/)

---

## ✨ Features
- 🕵️ Scraper for [Encar.com](https://www.encar.com)  
- 🚗 Extracts key details: **brand, model, year, mileage, price, image, link**  
- 📄 Saves data into [`site/data/cars.json`](site/data/cars.json)  
- 🌐 Responsive landing page (`site/index.html`)  
- ⚙️ Automated daily update via **GitHub Actions**  
- 📱 Mobile & desktop friendly  

---

## 🖥️ Local Setup

Clone the repository:
```bash
git clone https://github.com/OfUndefiend/encar-parser-landing.git
cd encar-parser-landing
```
## 1. Run the scraper
```bash

cd scraper
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python scraper.py


Result is saved into ../site/data/cars.json.
```
## 2. Start local server for landing page
```bash
cd ../site
python -m http.server 8000


Then open: http://localhost:8000
```
---
## ⚡ Automation (CI/CD)

This repo includes a GitHub Actions workflow:

Runs scraper daily (.github/workflows/scrape.yml)

Commits fresh data to site/data/cars.json

GitHub Pages automatically updates the live site
