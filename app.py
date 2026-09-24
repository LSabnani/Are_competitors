import re
import time
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Cache storage: key = ticker or lowercase query, value = (timestamp, data)
CACHE_TTL = 86400  # 24 hours
CACHE = {}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Known tickers for quick lookup & fallback summaries
KNOWN_COMPANIES = {
    "ford": {"ticker": "F", "name": "Ford Motor Company", "exchange": "NYSE"},
    "ford motor": {"ticker": "F", "name": "Ford Motor Company", "exchange": "NYSE"},
    "ford motor company": {"ticker": "F", "name": "Ford Motor Company", "exchange": "NYSE"},
    "gm": {"ticker": "GM", "name": "General Motors Company", "exchange": "NYSE"},
    "general motors": {"ticker": "GM", "name": "General Motors Company", "exchange": "NYSE"},
    "general motors company": {"ticker": "GM", "name": "General Motors Company", "exchange": "NYSE"},
    "toyota": {"ticker": "TM", "name": "Toyota Motor Corporation", "exchange": "NYSE"},
    "tm": {"ticker": "TM", "name": "Toyota Motor Corporation", "exchange": "NYSE"},
    "toyota motor": {"ticker": "TM", "name": "Toyota Motor Corporation", "exchange": "NYSE"},
    "toyota motor corporation": {"ticker": "TM", "name": "Toyota Motor Corporation", "exchange": "NYSE"},
    "tesla": {"ticker": "TSLA", "name": "Tesla, Inc.", "exchange": "NASDAQ"},
    "rivian": {"ticker": "RIVN", "name": "Rivian Automotive, Inc.", "exchange": "NASDAQ"},
    "apple": {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
    "microsoft": {"ticker": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
    "boeing": {"ticker": "BA", "name": "The Boeing Company", "exchange": "NYSE"},
    "spacex": {"is_public": False, "message": "SpaceX is a private company and is not publicly traded on stock exchanges."},
    "stripe": {"is_public": False, "message": "Stripe is currently a private company and not publicly traded on stock exchanges."},
}

DEFAULT_SUMMARIES = {
    "F": "Ford Motor Company designs, manufactures, markets and services cars, trucks, sport utility vehicles, electrified vehicles, and Lincoln luxury vehicles. Apart from vehicles, the company provides financial services through Ford Motor Credit Company LLC. Ford has three reportable operating segments: Automotive, Mobility (Ford Smart Mobility LLC), and Ford Credit.",
    "GM": "General Motors Company designs, builds, and sells trucks, crossovers, cars, and automobile parts worldwide. The company operates through GM Automotive, GM Financial, and Cruise autonomous vehicle technology segments. GM produces vehicles under Chevrolet, Buick, GMC, and Cadillac brands.",
    "TM": "Toyota Motor Corporation designs, manufactures, assembles, and sells passenger vehicles, minivans and commercial vehicles, and related parts and accessories in Japan, North America, Europe, Asia, Central and South America, Oceania, Africa, the Middle East, and internationally. The company operates through Automotive, Financial Services, and All Other segments.",
    "TSLA": "Tesla, Inc. designs, develops, manufactures, sells, and leases electric vehicles, energy generation and storage systems, and offers services related to its products. Segments include Automotive and Energy Generation & Storage.",
    "RIVN": "Rivian Automotive, Inc. designs, develops, and manufactures category-defining electric vehicles and accessories. It produces consumer vehicles including the R1T pickup and R1S SUV, alongside commercial electric delivery vans (EDVs).",
    "AAPL": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories, and sells a variety of related services. Products include iPhone, Mac, iPad, Apple Watch, and services like Apple Music, iCloud, and Apple Pay.",
    "MSFT": "Microsoft Corporation develops and supports software, services, devices and solutions. Segments include Productivity and Business Processes (Office, LinkedIn), Intelligent Cloud (Azure), and More Personal Computing (Windows, Xbox, Surface).",
    "BA": "The Boeing Company designs, manufactures, and services commercial jetliners, defense products, satellites, and space systems. Operating segments include Commercial Airplanes, Defense, Space & Security, and Global Services.",
}

KNOWN_PRIVATE_COMPANIES = {
    "spacex": "SpaceX is a private company and is not publicly traded on stock exchanges.",
    "stripe": "Stripe is currently a private company and not publicly traded on stock exchanges.",
    "bytedance": "ByteDance is a private company and is not listed on public stock exchanges.",
    "openai": "OpenAI is currently a private organization and is not publicly traded.",
    "epic games": "Epic Games is a private company and is not publicly traded.",
}

def resolve_ticker_finviz(query: str):
    """Generic ticker resolution for ANY company name or ticker symbol."""
    q_clean = query.strip().lower()
    
    # 1. Check known private companies registry
    if q_clean in KNOWN_PRIVATE_COMPANIES:
        return None, query.title(), False, KNOWN_PRIVATE_COMPANIES[q_clean]

    # 2. Check known overrides dict
    if q_clean in KNOWN_COMPANIES:
        item = KNOWN_COMPANIES[q_clean]
        if item.get("is_public") is False:
            return None, query.title(), False, item.get("message")
        return item["ticker"], item["name"], True, None

    # 3. Generic Financial Market Search Query (Global Exchanges)
    try:
        search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(query)}&quotesCount=5&newsCount=0"
        res = requests.get(search_url, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            quotes = res.json().get('quotes', [])
            for q in quotes:
                if q.get('quoteType') == 'EQUITY' and q.get('symbol'):
                    sym = q['symbol']
                    name = q.get('longname') or q.get('shortname') or query.title()
                    return sym, name, True, None
    except Exception:
        pass

    # 4. Direct Ticker Check via yfinance
    try:
        import yfinance as yf
        t = yf.Ticker(query.strip().upper())
        info = t.info
        if info and 'symbol' in info and info.get('quoteType') == 'EQUITY':
            return info['symbol'], info.get('longName', query.title()), True, None
    except Exception:
        pass

    # 5. Finviz Search Suggestions Endpoint Fallback
    try:
        f_url = f"https://finviz.com/api/suggestions.ashx?q={requests.utils.quote(query)}"
        res = requests.get(f_url, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                ticker = first.get('ticker')
                name = first.get('name', query.title())
                if ticker:
                    return ticker, name, True, None
    except Exception:
        pass

    return None, query.title(), False, f"{query.title()} may not be public"




def fetch_barchart_summary(symbol: str, official_name: str):
    """Fetch complete business summary overview from barchart.com or yfinance fallback."""
    cache_key = f"barchart_{symbol}"
    now = time.time()
    if cache_key in CACHE:
        ts, data = CACHE[cache_key]
        if now - ts < CACHE_TTL:
            return data

    source_url = f"https://www.barchart.com/stocks/quotes/{symbol}/overview"
    summary_text = None

    # Step 1: Attempt HTML scrape from Barchart
    try:
        res = requests.get(source_url, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            profile_div = soup.find('div', class_=re.compile(r'overview|description|profile', re.I))
            if profile_div:
                paragraphs = profile_div.find_all('p')
                if paragraphs:
                    extracted = ' '.join([p.text.strip() for p in paragraphs if len(p.text.strip()) > 30])
                    if len(extracted) > 60:
                        summary_text = extracted

            if not summary_text:
                meta_desc = soup.find('meta', {'name': 'description'})
                if meta_desc and meta_desc.get('content') and len(meta_desc['content']) > 60:
                    summary_text = meta_desc['content']
    except Exception:
        pass

    # Step 2: Fetch full long business summary via yfinance if Barchart output is truncated/empty
    if not summary_text or len(summary_text) < 60:
        try:
            import yfinance as yf
            t = yf.Ticker(symbol)
            info = t.info
            if info and info.get('longBusinessSummary'):
                summary_text = info['longBusinessSummary']
        except Exception:
            pass

    # Step 3: Default dictionary fallback
    if not summary_text or len(summary_text) < 40:
        summary_text = DEFAULT_SUMMARIES.get(
            symbol,
            f"{official_name} ({symbol}) is a publicly traded company on major stock exchanges. Full financial profile and business details can be viewed on Barchart."
        )

    result = {
        "summary": summary_text,
        "sourceUrl": source_url
    }
    CACHE[cache_key] = (now, result)
    return result



def generate_4_bullet_slide(summary_text: str, official_name: str):
    """Generate 4 bullet points for the company summary slide."""
    sentences = [s.strip() for s in re.split(r'\. |\n', summary_text) if len(s.strip()) > 20]
    bullets = []

    if len(sentences) >= 4:
        bullets = [
            f"**Core Products & Offerings**: {sentences[0]}.",
            f"**Operating Divisions**: {sentences[1]}.",
            f"**Financial & Services Operations**: {sentences[2]}.",
            f"**Market Presence**: {sentences[3]}."
        ]
    else:
        # Fallback structured bullets
        bullets = [
            f"**Core Business**: {summary_text[:120]}...",
            f"**Primary Operations**: Operates as a major public entity under {official_name}.",
            f"**Services & Subsidiaries**: Delivers specialized products, services, and financial solutions worldwide.",
            f"**Market Overview**: Listed on public stock exchanges with detailed data on Barchart."
        ]
    return bullets


def format_currency(val):
    if val is None or val == "N/A":
        return "N/A"
    try:
        val = float(val)
        abs_val = abs(val)
        prefix = "-" if val < 0 else ""
        if abs_val >= 1e12:
            return f"{prefix}${abs_val / 1e12:.2f}T"
        elif abs_val >= 1e9:
            return f"{prefix}${abs_val / 1e9:.2f}B"
        elif abs_val >= 1e6:
            return f"{prefix}${abs_val / 1e6:.2f}M"
        else:
            return f"{prefix}${abs_val:,.2f}"
    except Exception:
        return str(val)


def fetch_financial_statements(symbol: str):
    """Fetch latest Income Statement, Balance Sheet, and Sector/Industry metrics via yfinance."""
    cache_key = f"financials_{symbol}"
    now = time.time()
    if cache_key in CACHE:
        ts, data = CACHE[cache_key]
        if now - ts < CACHE_TTL:
            return data

    fin_data = {
        "sector": "General Market",
        "industry": "Commercial Operations",
        "marketCap": "N/A",
        "rawMarketCap": 0,
        "rawRevenue": 0,
        "incomeStatement": {
            "totalRevenue": "N/A",
            "grossProfit": "N/A",
            "operatingIncome": "N/A",
            "netIncome": "N/A",
            "trailingEps": "N/A"
        },
        "balanceSheet": {
            "totalCash": "N/A",
            "totalDebt": "N/A",
            "bookValue": "N/A",
            "equity": "N/A"
        }
    }

    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        info = t.info or {}
        fin_data["sector"] = info.get('sector', 'General Market')
        fin_data["industry"] = info.get('industry', 'Commercial Operations')
        fin_data["marketCap"] = format_currency(info.get('marketCap'))
        fin_data["rawMarketCap"] = info.get('marketCap') or 0
        fin_data["rawRevenue"] = info.get('totalRevenue') or 0

        fin_data["incomeStatement"]["totalRevenue"] = format_currency(info.get('totalRevenue'))
        fin_data["incomeStatement"]["grossProfit"] = format_currency(info.get('grossProfits'))
        fin_data["incomeStatement"]["operatingIncome"] = f"{info.get('operatingMargins', 0) * 100:.2f}%" if info.get('operatingMargins') is not None else "N/A"
        fin_data["incomeStatement"]["netIncome"] = format_currency(info.get('netIncomeToCommon'))
        fin_data["incomeStatement"]["trailingEps"] = f"${info.get('trailingEps'):.2f}" if info.get('trailingEps') is not None else "N/A"

        fin_data["balanceSheet"]["totalCash"] = format_currency(info.get('totalCash'))
        fin_data["balanceSheet"]["totalDebt"] = format_currency(info.get('totalDebt'))
        fin_data["balanceSheet"]["bookValue"] = f"${info.get('bookValue'):.2f}" if info.get('bookValue') is not None else "N/A"
    except Exception:
        pass

    CACHE[cache_key] = (now, fin_data)
    return fin_data


@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')


@app.route('/api/v1/clear_cache', methods=['POST'])
@app.route('/api/clear_cache', methods=['POST'])
def clear_cache():
    CACHE.clear()
    return jsonify({"status": "success", "message": "Cache cleared successfully."})


@app.route('/api/compare', methods=['POST'])
@app.route('/api/v1/compare', methods=['POST'])
def compare_companies():
    payload = request.get_json() or {}
    company_a = payload.get('companyA', '').strip()
    company_b = payload.get('companyB', '').strip()
    ticker_a = payload.get('tickerA', '').strip()
    ticker_b = payload.get('tickerB', '').strip()

    if not company_a or not company_b:
        return jsonify({
            "status": "error",
            "errorCode": "ERR_INVALID_INPUT",
            "message": "Both Company A and Company B names must be provided."
        }), 400

    def process_company(query_name, explicit_ticker=None):
        if explicit_ticker:
            ticker = explicit_ticker.upper()
            official_name = query_name.title()
            is_public = True
            err_msg = None
        else:
            ticker, official_name, is_public, err_msg = resolve_ticker_finviz(query_name)

        if not is_public or not ticker:
            return {
                "inputName": query_name,
                "isPublic": False,
                "message": err_msg or f"{query_name.title()} may not be public"
            }

        barchart_data = fetch_barchart_summary(ticker, official_name)
        bullets = generate_4_bullet_slide(barchart_data["summary"], official_name)
        financials = fetch_financial_statements(ticker)

        return {
            "inputName": query_name,
            "officialName": official_name,
            "ticker": ticker,
            "exchange": "NYSE/NASDAQ",
            "isPublic": True,
            "sourceUrl": barchart_data["sourceUrl"],
            "summary": barchart_data["summary"],
            "bullets": bullets,
            "financials": financials
        }

    res_a = process_company(company_a, ticker_a)
    res_b = process_company(company_b, ticker_b)


    # Determine Common Market Segment & Market Size Footprint
    market_analysis = None
    if res_a.get("isPublic") and res_b.get("isPublic"):
        fin_a = res_a.get("financials", {})
        fin_b = res_b.get("financials", {})

        ind_a = fin_a.get("industry", "")
        ind_b = fin_b.get("industry", "")
        sec_a = fin_a.get("sector", "")
        sec_b = fin_b.get("sector", "")

        # Common segment matching
        if ind_a and ind_a == ind_b:
            common_segment = f"{ind_a} ({sec_a})"
            overlap_type = "Direct Industry Competitors"
        elif sec_a and sec_a == sec_b:
            common_segment = f"{sec_a} Sector ({ind_a} / {ind_b})"
            overlap_type = "Sector Competitors"
        else:
            common_segment = f"{ind_a} & {ind_b}"
            overlap_type = "Cross-Segment Competitors"

        rev_a = fin_a.get("rawRevenue", 0) or 0
        rev_b = fin_b.get("rawRevenue", 0) or 0
        combined_cap = (fin_a.get("rawMarketCap", 0) or 0) + (fin_b.get("rawMarketCap", 0) or 0)
        combined_rev = rev_a + rev_b

        # Segment Market Size (TAM) Estimates & Share Calculation
        tam_map = {
            'auto manufacturers': 2500000000000,
            'consumer electronics': 1200000000000,
            'semiconductors': 650000000000,
            'software - infrastructure': 850000000000,
            'aerospace & defense': 750000000000,
            'internet content & information': 1100000000000,
            'beverages - non-alcoholic': 450000000000,
            'footwear & accessories': 380000000000,
            'drug manufacturers - general': 1150000000000,
        }
        ind_key = ind_a.lower() if ind_a else sec_a.lower()
        tam_val = tam_map.get(ind_key, max((combined_rev * 3.5), 100000000000))


        share_a_val = min(round((rev_a / tam_val) * 100, 2), 99.0) if tam_val > 0 else 0
        share_b_val = min(round((rev_b / tam_val) * 100, 2), 99.0) if tam_val > 0 else 0
        remaining_val = max(round(100.0 - share_a_val - share_b_val, 2), 0.0)

        leader = res_a.get("officialName") if rev_a >= rev_b else res_b.get("officialName")

        market_analysis = {
            "commonSegment": common_segment,
            "overlapType": overlap_type,
            "segmentMarketSize": format_currency(tam_val),
            "combinedMarketCap": format_currency(combined_cap),
            "combinedRevenue": format_currency(combined_rev),
            "shareA": f"{share_a_val:.2f}%",
            "shareB": f"{share_b_val:.2f}%",
            "remainingShare": f"{remaining_val:.2f}%",
            "rawShareA": share_a_val,
            "rawShareB": share_b_val,
            "rawRemaining": remaining_val,
            "marketLeader": leader,
            "marketCapA": fin_a.get("marketCap", "N/A"),
            "marketCapB": fin_b.get("marketCap", "N/A"),
            "industryA": ind_a,
            "industryB": ind_b
        }


    all_public = res_a.get("isPublic") and res_b.get("isPublic")
    status = "success" if all_public else "partial_success"

    return jsonify({
        "status": status,
        "timestamp": time.strftime("%Y-%m-%d%z"),
        "query": {
            "companyA": company_a,
            "companyB": company_b
        },
        "marketAnalysis": market_analysis,
        "data": {
            "companyA": res_a,
            "companyB": res_b
        }
    })





if __name__ == '__main__':
    print("Starting Competitor & Market Analysis Agent on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
