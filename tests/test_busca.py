
import pytest
from busca import extract_contacts

def test_extract_contacts_email():
    html = """
    <html>
        <body>
            <p>Contact us at test@example.com or support@domain.co.uk</p>
            <a href="mailto:info@company.com">Email Us</a>
        </body>
    </html>
    """
    url = "http://example.com"
    email, phone, socials = extract_contacts(html, url)
    
    assert "test@example.com" in email
    assert "support@domain.co.uk" in email
    assert "info@company.com" in email

def test_extract_contacts_phone():
    html = """
    <html>
        <body>
            <p>Call us: (11) 98765-4321</p>
            <a href="tel:0800123456">Ligue Grátis</a>
        </body>
    </html>
    """
    url = "http://example.com"
    email, phone, socials = extract_contacts(html, url)
    
    # Needs to match the regex used in busca.py
    # PHONE_RE = re.compile(r"\(?\d{2}\)?\s*\d{4,5}[.\-\s]?\d{4}")
    assert "(11) 98765-4321" in phone
    assert "0800123456" in phone

def test_extract_contacts_socials():
    html = """
    <html>
        <body>
            <a href="https://facebook.com/company">Facebook</a>
            <a href="https://instagram.com/company">Instagram</a>
            <a href="https://twitter.com/company">Twitter</a>
        </body>
    </html>
    """
    url = "http://example.com"
    email, phone, socials = extract_contacts(html, url)
    
    assert "https://facebook.com/company" in socials
    assert "https://instagram.com/company" in socials
    assert "https://twitter.com/company" in socials

def test_extract_contacts_empty():
    html = "<html><body><p>No contact info here.</p></body></html>"
    url = "http://example.com"
    email, phone, socials = extract_contacts(html, url)
    
    assert email == "N/A"
    assert phone == "N/A"
    assert socials == "N/A"
