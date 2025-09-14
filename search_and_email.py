#!/usr/bin/env python3
"""
Daily job search script using SerpAPI (Google Results API).
Filters for entry-level DevOps/Cloud roles in Bangalore, Hyderabad, Pune,
and emails results.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from serpapi import GoogleSearch
from bs4 import BeautifulSoup
from datetime import datetime

# Config (env vars)
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
RECIPIENT = os.getenv("RECIPIENT_EMAIL", "pnarayankar876@gmail.com")

# Search settings
locations = ["Bangalore", "Bengaluru", "Hyderabad", "Pune"]
roles = ["DevOps Engineer", "Cloud Engineer", "DevOps", "Site Reliability Engineer", "SRE"]
experience_keywords = ["entry level", "0 years", "0-1", "0 to 1", "fresher", "0-1 years", "fresher", "graduate", "new grad"]
site_filters = ["angel.co", "linkedin.com", "indeed.com", "instahyre.com", "cutshort.io"]

MAX_RESULTS_PER_QUERY = 10

def build_queries():
    queries = []
    for loc in locations:
        for role in roles:
            # include startup keyword to prioritize startup postings
            q = f"{role} startup entry level {loc}"
            queries.append(q)
            # search without "startup" also
            queries.append(f"{role} entry level {loc}")
    return queries

def search_serpapi(query):
    params = {
        "engine": "google",
        "q": query,
        "hl": "en",
        "google_domain": "google.com",
        "api_key": SERPAPI_KEY,
        "num": MAX_RESULTS_PER_QUERY
    }
    search = GoogleSearch(params)
    result = search.get_dict()
    return result

def extract_links_from_serp(result):
    links = []
    # serpapi returns 'organic_results' with 'link' and 'snippet'
    for r in result.get("organic_results", []):
        link = r.get("link")
        title = r.get("title")
        snippet = r.get("snippet")
        if link:
            links.append({"link": link, "title": title, "snippet": snippet})
    return links

def filter_and_score(items):
    filtered = []
    for it in items:
        text = " ".join(filter(None, [it.get("title",""), it.get("snippet","")])).lower()
        # require at least one experience keyword and one role keyword
        if any(k in text for k in experience_keywords) or "entry" in text or "fresher" in text:
            if any(r.lower() in text for r in roles):
                # check location
                if any(loc.lower() in text for loc in locations):
                    filtered.append(it)
                else:
                    # still include if location in link domain or title
                    filtered.append(it)
    # dedupe by link
    seen = set()
    dedup = []
    for f in filtered:
        if f["link"] not in seen:
            dedup.append(f)
            seen.add(f["link"])
    return dedup

def build_email_body(results):
    now = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    if not results:
        return f"Subject: Daily Job Search — No new matching jobs found ({now})\n\nNo matching jobs were found in today's search."
    lines = [f"Daily Job Search results ({now})\n", "-"*60]
    for i, r in enumerate(results, 1):
        title = r.get("title") or "No title"
        link = r.get("link")
        snippet = r.get("snippet") or ""
        lines.append(f"{i}. {title}\n{snippet}\n{link}\n")
    return "\n".join(lines)

def send_email(subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = formataddr(("Job Bot", SMTP_USER))
    msg["To"] = RECIPIENT
    msg["Subject"] = subject

    # Gmail SMTP example uses smtp.gmail.com:587
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SMTP_USER, SMTP_PASS)
    server.sendmail(SMTP_USER, RECIPIENT, msg.as_string())
    server.quit()

def main():
    if not SERPAPI_KEY:
        raise SystemExit("SERPAPI_KEY not configured")
    queries = build_queries()
    all_links = []
    for q in queries:
        try:
            res = search_serpapi(q)
            links = extract_links_from_serp(res)
            all_links.extend(links)
        except Exception as e:
            # continue on errors
            print("Search error:", e)
    final = filter_and_score(all_links)
    # Keep top 25 matches
    final = final[:25]
    body = build_email_body(final)
    subject = f"Daily Job Search — {len(final)} matches"
    send_email(subject, body)
    print("Email sent to", RECIPIENT)

if __name__ == "__main__":
    main()
