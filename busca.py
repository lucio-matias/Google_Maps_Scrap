import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

SOCIAL_DOMAINS = [
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(
    r"\(?\d{2}\)?\s*\d{4,5}[.\-\s]?\d{4}"
)


def extract_contacts(html, url):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    # --- Emails ---
    emails = set()
    for a in soup.select("a[href^='mailto:']"):
        addr = a["href"].replace("mailto:", "").split("?")[0].strip()
        if addr:
            emails.add(addr.lower())
    for m in EMAIL_RE.findall(text):
        if not m.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
            emails.add(m.lower())

    # --- Telefones ---
    phones = set()
    for a in soup.select("a[href^='tel:']"):
        raw = a["href"].replace("tel:", "").strip()
        if raw:
            phones.add(raw)
    for m in PHONE_RE.findall(text):
        phones.add(m.strip())

    # --- Redes sociais ---
    socials = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        for domain in SOCIAL_DOMAINS:
            if domain in href:
                socials.add(href.split("?")[0].rstrip("/"))
                break

    return (
        " | ".join(sorted(emails)) or "N/A",
        " | ".join(sorted(phones)) or "N/A",
        " | ".join(sorted(socials)) or "N/A",
    )


def main(input_file="output.csv", output_file="busca.csv", progress_callback=None):
    df = pd.read_csv(input_file)
    rows = []
    total = len(df)

    for i, row in df.iterrows():
        name = row.get("Name", "N/A")
        address = row.get("Full Address", "N/A")
        url = row.get("URL", "N/A")

        email, phone, socials = "N/A", "N/A", "N/A"

        if pd.notna(url) and url != "N/A":
            try:
                resp = requests.get(url, headers=HEADERS, timeout=10, verify=True)
                resp.raise_for_status()
                email, phone, socials = extract_contacts(resp.text, url)
            except requests.exceptions.SSLError:
                print(f"  [SSL erro] {name} — {url}")
            except requests.exceptions.ConnectionError:
                print(f"  [Conexão erro] {name} — {url}")
            except requests.exceptions.Timeout:
                print(f"  [Timeout] {name} — {url}")
            except requests.exceptions.RequestException as e:
                print(f"  [Erro] {name} — {e}")

        rows.append({
            "Name": name,
            "Full Address": address,
            "Email": email,
            "Telefone": phone,
            "URL": url,
            "Redes Sociais": socials,
        })
        print(f"Empresa {i + 1}/{total} processada: {name}")
        if progress_callback:
            progress_callback(i + 1, total)

    out = pd.DataFrame(rows)
    if output_file.endswith(".xlsx"):
        out.to_excel(output_file, index=False)
    else:
        out.to_csv(output_file, index=False)
    print(f"\nArquivo '{output_file}' gerado com {len(out)} registros.")


if __name__ == "__main__":
    main()
