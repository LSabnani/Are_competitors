# Company Competitor Analysis Agent (`Are they competitors?`)

An intelligent web-based market analysis application that answers **"Are they competitors?"** by verifying stock exchange existence and ticker symbols on **Finviz** and retrieving detailed business overview summaries from **Barchart**.

---

## 🌟 Core Features & Questions Answered

1. **Market Existence Check (`finviz.com`)**:
   - Searches Finviz for user-specified company names (`Company A` & `Company B`).
   - Resolves active ticker symbols (e.g. `F` for Ford, `GM` for General Motors).
   - If a company is private or unlisted, outputs: `<Company Name> may not be public`.

2. **Business Summary Retrieval (`barchart.com`)**:
   - Fetches corporate overview descriptions from `barchart.com/stocks/quotes/{SYMBOL}/overview`.
   - Includes business segments (e.g. Automotive, Mobility, Ford Credit).

3. **Interactive Re-prompt Loop**:
   - Asks user **"Any more pairs needed? (Y/N)"** via the Web UI to reset inputs or continue comparing pairs.

---

## 🚀 Setup & Execution Guide

### Prerequisites
- Python 3.9+ installed on your system.

### Installation Steps

1. **Navigate to Project Directory**:
   ```powershell
   cd c:\Users\Lalit.MSI\Documents\Education\AntiGravity\my_app\Competitors\Are_competitors
   ```

2. **Create & Activate Virtual Environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate.ps1
   ```

3. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Run Web Application**:
   ```powershell
   python app.py
   ```

5. **Access Application**:
   Open browser at: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 📄 Specification Reference

For the complete requirement specification, see [`spec.md`](file:///c:/Users/Lalit.MSI/Documents/Education/AntiGravity/my_app/Competitors/Are_competitors/spec.md).

---

## 🔗 Data Sources

- **Finviz**: `https://finviz.com` (Ticker symbol resolution & market existence check)
- **Barchart**: `https://www.barchart.com/stocks/quotes/<SYMBOL>/overview` (Business overview summaries)
