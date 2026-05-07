import ollama
import json, re
from tenacity import retry, stop_after_attempt, wait_fixed
import httpx
from bs4 import BeautifulSoup

"""
| Model        | Time per request |
| ------------ | ---------------- |
| qwen2.5:7b   | 5~20 sec         |
| qwen2.5:3b   | 2~8 sec          |
| qwen2.5:1.5b | 1~3 sec          |

"""


MODEL = "qwen2.5:7b"

# ---------------- CLOUDFARE EMAIL DECODE ----------------
def decode_cfemail(cfemail):
    try:
        r = int(cfemail[:2], 16)
        email = ""
        for i in range(2, len(cfemail), 2):
            email += chr(int(cfemail[i:i+2], 16) ^ r)
        return email
    except Exception:
        return ""

def decode_emails_inplace(soup):
    """Find all Cloudflare-protected emails and decode them in the soup directly."""
    for span in soup.find_all("span", attrs={"data-cfemail": True}):
        encoded = span["data-cfemail"]
        real_email = decode_cfemail(encoded)
        
        # Update the span text and remove the obfuscation attribute
        span.string = real_email
        del span["data-cfemail"]

        # Also update the parent <a> href if it's a mailto
        parent_a = span.find_parent("a")
        if parent_a and "href" in parent_a.attrs:
            parent_a["href"] = f"mailto:{real_email}"

    return soup

def clean_html(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")

    soup = decode_emails_inplace(soup)  # Decode Cloudflare emails directly in the soup for better extraction

    # Remove noise tags entirely
    for tag in soup(["script", "style", "noscript", "iframe","link",  "svg"]):
        tag.decompose()

    websites = soup.select("a[href^='http'], a[href^='www']")
    extract_website = []
    for data in websites:
        href = data.get("href", "")
        extract_website.append(href)

    # # Get plain text
    text = soup.get_text(separator=" ", strip=True)

    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text, extract_website

def build_prompt(text, url_norm, website=[]):
    return f"""
        Extract structured contact data from the text.

        Return ONLY valid JSON. No explanation. No markdown.

        Schema:
        {{
        "company": "",
        "address": "",
        "emails": [],
        "website": "",
        "phone": "",
        "people": [
            {{
            "name": "",
            "designation": "",
            "email": ""
            }}
        ]
        }}

        Rules:
        - Extract company, address, phone, emails, people
        - Collect ALL emails into "emails" (no duplicates)
        - If a person has email, include it in both places
        - Prefer company website over directory/listing sites
        - Ignore social media links
        - Extract ONLY information explicitly present in the text
        - If a field is not clearly present, return it as empty ("", [] as applicable)
        - Only include data that is clearly and directly stated
        - Prefer person-specific email over general emails
        - If multiple phones, return the main one
        - If multiple websites found, choose most relevant company domain
        - Always return valid JSON (double quotes only)
        - Do NOT add, infer, or guess any data
        - Do NOT construct or modify emails, phone numbers, or websites
        - Do NOT assume company website from email domain unless explicitly present
        - Do NOT complete partial addresses or names
        - Main website is {url_norm} if it appears in the text, otherwise choose from candidate websites

        Candidate websites:
        {json.dumps(website)}

        Text:
        {text}
        """

def extract_json_from_qwen_response(raw: str) -> dict:
    """
    Handles all Qwen response formats:
    - Clean JSON
    - ```json ... ``` wrapped
    - ``` ... ``` wrapped  
    - JSON buried in text
    """
    if not raw:
        return {}

    text = raw.strip()

    # 1. Strip ```json ... ``` or ``` ... ``` fences
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # 2. Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Find first { ... } block in case there's surrounding text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 4. Give up
    return {}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
def extract_with_qwen(raw_html, url_norm):
    error = None
    try:
        text, extract_website = clean_html(raw_html)
        
        prompt = build_prompt(text, url_norm, website=extract_website)

        # Use a custom httpx client with timeout
        client = ollama.Client(
            host="http://127.0.0.1:11434",
            timeout=httpx.Timeout(600.0, connect=5.0)  # 600s read, 5s connect
        )

        response = client.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": 0.1,
                "num_predict": 600
            }
        )

        content = response["message"]["content"]
        content_data = []
        content_data.append(extract_json_from_qwen_response(content))
        return content_data, error

    except httpx.ReadTimeout:
        print("⏱️ TIMEOUT: Ollama took too long, retrying...")
        return [], "⏱️ TIMEOUT: Ollama took too long, retrying..."
    except Exception as e:
        print("🔥 ERROR:", str(e))
        return [], "🔥 ERROR:" +str(e)