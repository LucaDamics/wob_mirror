"""Download the EC Weekly Oil Bulletin spreadsheets into data/.

Finds every .xlsx link on the bulletin page, so it keeps working when the
Commission changes the document IDs. Saves each file twice:
  data/latest/<name>.xlsx                always the newest copy
  data/archive/<YYYY-MM-DD>/<name>.xlsx  dated snapshot of this run
The workflow only commits when a file has actually changed.
"""
import datetime as dt
import pathlib
import re
import sys
import urllib.parse

import requests

PAGE = "https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en"
BASE = "https://energy.ec.europa.eu"
HEADERS = {"User-Agent": "Mozilla/5.0 (wob-mirror; personal research)"}

# The price history file has a stable link; kept as a fallback in case
# the page layout changes and the scrape finds nothing.
HISTORY_URL = (
    "https://energy.ec.europa.eu/document/download/"
    "906e60ca-8b6a-44e7-8589-652854d2fd3f_en"
    "?filename=Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx"
)


def find_xlsx_links(html):
    links = set()
    for href in re.findall(r'href="([^"]+)"', html):
        href = href.replace("&amp;", "&")
        if ".xlsx" in href.lower():
            links.add(urllib.parse.urljoin(BASE, href))
    return sorted(links)


def clean_name(url):
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    name = query.get("filename", [url.rsplit("/", 1)[-1]])[0]
    name = urllib.parse.unquote(name)
    # Drop the date the EC puts in some filenames so "latest" keeps one name.
    name = re.sub(r"\s*-\s*\d{4}-\d{2}-\d{2}", "", name)
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def main():
    page = requests.get(PAGE, headers=HEADERS, timeout=60)
    page.raise_for_status()
    links = find_xlsx_links(page.text)
    if HISTORY_URL not in links:
        links.append(HISTORY_URL)
    print(f"Found {len(links)} xlsx links")

    today = dt.date.today().isoformat()
    latest = pathlib.Path("data/latest")
    archive = pathlib.Path("data/archive") / today
    latest.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)

    ok = 0
    for url in links:
        name = clean_name(url)
        r = requests.get(url, headers=HEADERS, timeout=120)
        if r.status_code != 200 or not r.content.startswith(b"PK"):
            print(f"SKIP {name}: status {r.status_code}, not an xlsx")
            continue
        (latest / name).write_bytes(r.content)
        (archive / name).write_bytes(r.content)
        print(f"OK   {name} ({len(r.content):,} bytes)")
        ok += 1

    if ok == 0:
        sys.exit("No spreadsheets downloaded")


if __name__ == "__main__":
    main()
