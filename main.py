from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup

app = FastAPI()

# Allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = "https://agriwelfare.gov.in"
KARNATAKA_URL = "https://raitamitra.karnataka.gov.in/english"

# ================= CENTRAL SCHEMES ================= #
@app.get("/schemes/central")
def get_central_schemes():
    url = f"{BASE_URL}/en/Major"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table")  # the main schemes table
        schemes = []

        if table:
            rows = table.find_all("tr")[1:]  # skip header row
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 4:
                    title = cols[1].get_text(strip=True)
                    date = cols[2].get_text(strip=True)
                    link_tag = cols[3].find("a")
                    link = BASE_URL + link_tag["href"] if link_tag and link_tag.get("href") else "#"

                    schemes.append({
                        "title": title,
                        "date": date,
                        "link": link
                    })

        return {"category": "central", "schemes": schemes}

    except Exception as e:
        return {
            "category": "central",
            "schemes": [{"title": f"Error fetching data: {e}", "date": "", "link": "#"}]
        }



# ================= KARNATAKA SCHEMES (Hierarchical) ================= #
@app.get("/schemes/karnataka")
def get_karnataka_schemes():
    from urllib.parse import urljoin

    def parse_list(ul):
        """Recursively parse <ul> and return schemes with children."""
        schemes = []
        for li in ul.find_all("li", recursive=False):
            a = li.find("a", href=True)
            if not a:
                continue

            title = a.get_text(" ", strip=True)
            if not title:
                continue

            link = urljoin("https://raitamitra.karnataka.gov.in/", a["href"])

            # check for nested <ul> (children)
            child_ul = li.find("ul")
            children = parse_list(child_ul) if child_ul else []

            schemes.append({
                "title": title,
                "link": link,
                "children": children
            })
        return schemes

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = requests.get(KARNATAKA_URL, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Locate the "SERVICES AND SCHEMES" heading
        heading = soup.find(
            lambda t: (
                t.name in ["h1", "h2", "h3", "h4", "h5", "h6"]
                and "SERVICES AND SCHEMES" in t.get_text(" ", strip=True).upper()
            )
        )

        schemes = []
        if heading:
            # find the first <ul> after the heading
            ul = heading.find_next("ul")
            if ul:
                schemes = parse_list(ul)

        return {"category": "karnataka", "schemes": schemes}

    except Exception as e:
        return {
            "category": "karnataka",
            "schemes": [{"title": f"Error fetching data: {e}", "link": "#", "children": []}]
        }

#############################################################################################################
#############################################################################################################
#############################################################################################################

from fastapi.responses import HTMLResponse  # Add this import at the top

# ... (keep all your existing code exactly as it is) ...

# ================= WEB INTERFACE ================= #
@app.get("/", response_class=HTMLResponse)
async def serve_homepage():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KrishiSetu - Farmer Schemes Portal</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .header {
                background: linear-gradient(135deg, #2c786c, #004445);
                color: white;
                padding: 2rem 0;
                margin-bottom: 2rem;
                border-radius: 0 0 10px 10px;
            }
            .scheme-card {
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                margin-bottom: 1rem;
                border-left: 4px solid #28a745;
                transition: transform 0.2s;
            }
            .scheme-card:hover {
                transform: translateY(-3px);
            }
            .central-scheme {
                border-left-color: #28a745;
            }
            .karnataka-scheme {
                border-left-color: #17a2b8;
            }
            .child-scheme {
                margin-left: 2rem;
                border-left-color: #ffc107;
            }
            .nav-pills .nav-link.active {
                background-color: #2c786c;
            }
            .loading-spinner {
                display: none;
            }
            .scheme-date {
                font-size: 0.85rem;
                color: #6c757d;
            }
        </style>
    </head>
    <body>
        <div class="header text-center">
            <div class="container">
                <h1 class="display-4">KrishiSetu</h1>
                <p class="lead">Connecting farmers with government schemes</p>
            </div>
        </div>

        <div class="container">
            <ul class="nav nav-pills mb-4 justify-content-center">
                <li class="nav-item">
                    <a class="nav-link active" href="#" onclick="loadSchemes('central')">Central Schemes</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#" onclick="loadSchemes('karnataka')">Karnataka Schemes</a>
                </li>
            </ul>

            <div class="text-center loading-spinner" id="loadingSpinner">
                <div class="spinner-border text-success" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading schemes...</p>
            </div>

            <div id="schemesContainer" class="row"></div>
        </div>

        <footer class="mt-5 py-3 bg-light text-center">
            <div class="container">
                <p class="mb-0">© 2023 KrishiSetu - Farmer Welfare Initiative</p>
            </div>
        </footer>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            async function loadSchemes(type) {
                // Update active tab
                document.querySelectorAll('.nav-link').forEach(link => {
                    link.classList.remove('active');
                });
                event.target.classList.add('active');
                
                // Show loading spinner
                document.getElementById('loadingSpinner').style.display = 'block';
                document.getElementById('schemesContainer').innerHTML = '';
                
                try {
                    const response = await fetch(`/schemes/${type}`);
                    const data = await response.json();
                    
                    let html = '';
                    if (type === 'central') {
                        html = renderCentralSchemes(data.schemes);
                    } else {
                        html = renderKarnatakaSchemes(data.schemes);
                    }
                    
                    document.getElementById('schemesContainer').innerHTML = html;
                } catch (error) {
                    document.getElementById('schemesContainer').innerHTML = `
                        <div class="col-12">
                            <div class="alert alert-danger">Error loading schemes: ${error.message}</div>
                        </div>
                    `;
                } finally {
                    document.getElementById('loadingSpinner').style.display = 'none';
                }
            }
            
            function renderCentralSchemes(schemes) {
                if (schemes.length === 0) {
                    return '<div class="col-12"><p class="text-center">No schemes found</p></div>';
                }
                
                return schemes.map(scheme => `
                    <div class="col-md-6">
                        <div class="card scheme-card central-scheme mb-3">
                            <div class="card-body">
                                <h5 class="card-title">${scheme.title}</h5>
                                ${scheme.date ? `<p class="scheme-date">Date: ${scheme.date}</p>` : ''}
                                <a href="${scheme.link}" target="_blank" class="btn btn-sm btn-success">
                                    View Details
                                </a>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
            
            function renderKarnatakaSchemes(schemes, level = 0) {
                if (schemes.length === 0) {
                    return '<div class="col-12"><p class="text-center">No schemes found</p></div>';
                }
                
                return schemes.map(scheme => `
                    <div class="col-12">
                        <div class="card scheme-card ${level > 0 ? 'child-scheme' : 'karnataka-scheme'} mb-2">
                            <div class="card-body">
                                <h5 class="card-title">${scheme.title}</h5>
                                <a href="${scheme.link}" target="_blank" class="btn btn-sm btn-primary">
                                    View Details
                                </a>
                                ${scheme.children && scheme.children.length > 0 ? 
                                    `<div class="mt-3">${renderKarnatakaSchemes(scheme.children, level + 1)}</div>` : ''}
                            </div>
                        </div>
                    </div>
                `).join('');
            }
            
            // Load central schemes by default when page loads
            window.onload = loadSchemes('central');
        </script>
    </body>
    </html>
    """
#############################################################################################################
#############################################################################################################
#############################################################################################################

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import HTMLResponse
# from fastapi.staticfiles import StaticFiles

# import requests
# from bs4 import BeautifulSoup

# app = FastAPI()

# # Allow frontend to call API
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Serve static files (CSS, JS, etc.)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# # Serve frontend at "/"
# @app.get("/", response_class=HTMLResponse)
# def serve_frontend():
#     with open("index.html", "r", encoding="utf-8") as f:
#         return f.read()


# # ======================
# # Central Schemes Route
# # ======================
# @app.get("/schemes/central")
# def get_central_schemes():
#     # Example scraping (replace with your real scraping logic if needed)
#     url = "https://www.india.gov.in/my-government/schemes"
#     response = requests.get(url)
#     soup = BeautifulSoup(response.text, "html.parser")

#     schemes = []
#     for item in soup.select(".views-row"):
#         title = item.get_text(strip=True)
#         link = item.find("a")["href"] if item.find("a") else "#"
#         schemes.append({"title": title, "link": link})

#     # fallback if scraping fails
#     if not schemes:
#         schemes = [
#             {"title": "PM Kisan Samman Nidhi", "link": "https://pmkisan.gov.in/"},
#             {"title": "Ayushman Bharat Yojana", "link": "https://pmjay.gov.in/"},
#         ]

#     return {"schemes": schemes}


# # =========================
# # Karnataka Schemes Route
# # =========================
# @app.get("/schemes/karnataka")
# def get_karnataka_schemes():
#     # Example scraping (replace with real site later)
#     url = "https://sevasindhu.karnataka.gov.in/Sevasindhu/English"
#     response = requests.get(url)
#     soup = BeautifulSoup(response.text, "html.parser")

#     schemes = []
#     for item in soup.select("a"):
#         text = item.get_text(strip=True)
#         href = item.get("href", "#")
#         if "scheme" in text.lower():  # crude filter
#             schemes.append({"title": text, "link": href})

#     # fallback if scraping fails
#     if not schemes:
#         schemes = [
#             {"title": "Anna Bhagya Scheme", "link": "https://ahara.kar.nic.in/"},
#             {"title": "Gruha Jyothi Scheme", "link": "https://sevasindhugs.karnataka.gov.in/"},
#         ]

#     return {"schemes": schemes}
