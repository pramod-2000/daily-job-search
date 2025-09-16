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
from datetime import datetime

# =============================
# Config from environment
# =============================
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
RECIPIENT = os.getenv("RECIPIENT_EMAIL", "pnarayankar876@gmail.com")

# Validate env vars
missing = []
if not SERPAPI_KEY:
    missing.append("SERPAPI_KEY")
if not SMTP_USER:
    missing.append("SMTP_USER")
if not SMTP_PASS:
    missing.append("SMTP_PASS")

if missing:
    raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

# =============================
# Search settings
# =============================
locations = ["Bangalore", "Bengaluru", "Hyderabad", "Pune"]
roles = ["DevOps Engineer", "Cloud Engineer", "DevOps", "Site Reliability Engineer", "SRE"]
experience_keywords = ["entry level", "0 years", "0-1", "0 to 1", "fresher", "graduate", "new grad"]
MAX_RESULTS_PER_QUERY = 10


def build_queries():
    queries = []
    for loc in locations:
        for role in roles:
            queries.append(f"{role} startup entry level {loc}")
            queries.append(f"{role} entry level {loc}")
    return queries


def search_serpapi(query):
    params = {
        "engine": "google",
        "q": query,
        "hl": "en",
        "google_domain": "google.com",
        "api_key": SERPAPI_KEY,
        "num": MAX_RESULTS_PER_QUERY,
    }
    search = GoogleSearch(params)
    return search.get_dict()


def extract_links_from_serp(result):
    links = []
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
        text = " ".join(filter(None, [it.get("title", ""), it.get("snippet", "")])).lower()
        if any(k in text for k in experience_keywords) or "fresher" in text or "entry" in text:
            if any(r.lower() in text for r in roles):
                if any(loc.lower() in text for loc in locations):
                    filtered.append(it)
                else:
                    filtered.append(it)
    # Deduplicate
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
        return f"No matching jobs were found in today's search ({now})."
    lines = [f"Daily Job Search results ({now})", "-" * 60]
    for i, r in enumerate(results, 1):
        title = r.get("title") or "No title"
        link = r.get("link")
        snippet = r.get("snippet") or ""
        lines.append(f"{i}. {title}\n{snippet}\n{link}\n")
    return "\n".join(lines)


def send_email(subject, body):
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = formataddr(("Job Bot", SMTP_USER))
        msg["To"] = RECIPIENT
        msg["Subject"] = subject

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, RECIPIENT, msg.as_string())

        print("✅ Email sent successfully to", RECIPIENT)
    except Exception as e:
        print("❌ Email send failed:", str(e))


def main():
    queries = build_queries()
    all_links = []

    for q in queries:
        try:
            res = search_serpapi(q)
            links = extract_links_from_serp(res)
            all_links.extend(links)
        except Exception as e:
            print(f"Search error for query '{q}':", e)

    final = filter_and_score(all_links)[:25]
    body = build_email_body(final)
    subject = f"Daily Job Search — {len(final)} matches"
    send_email(subject, body)


if __name__ == "__main__":
    main()
