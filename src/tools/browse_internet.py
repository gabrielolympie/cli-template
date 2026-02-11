from mirascope import llm
import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse, urljoin
import re
import time
import random


def _extract_text(html_content: str, url: str = "", max_length: int = 10000) -> str:
    """Extract clean, structured text content from HTML.

    Args:
        html_content: Raw HTML content
        url: The source URL (used for resolving relative links)
        max_length: Maximum length of returned text

    Returns:
        Clean structured text content truncated to max_length
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove non-visible / non-content elements
        for tag in soup(
            [
                "script",
                "style",
                "noscript",
                "iframe",
                "svg",
                "canvas",
                "head",
                "header",
                "footer",
                "nav",
                "aside",
                "form",
                "button",
                "input",
                "select",
                "textarea",
            ]
        ):
            tag.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # Remove hidden elements
        for tag in soup.find_all(
            attrs={"style": re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden")}
        ):
            tag.decompose()
        for tag in soup.find_all(attrs={"hidden": True}):
            tag.decompose()
        for tag in soup.find_all(attrs={"aria-hidden": "true"}):
            tag.decompose()

        # ── Extract page title ──
        parts: list[str] = []
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            parts.append(f"# {title_tag.get_text(strip=True)}")

        # ── Extract meta description ──
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content", "").strip():
            parts.append(f"Description: {meta_desc['content'].strip()}")

        # ── Try to find the main content area first ──
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"role": "main"})
            or soup.find("div", {"id": re.compile(r"content|main|article", re.I)})
            or soup.find("div", {"class": re.compile(r"content|main|article", re.I)})
        )

        target = main_content if main_content else soup.body if soup.body else soup

        # ── Walk relevant tags and preserve basic structure ──
        for element in target.descendants:
            if element.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(element.name[1])
                text = element.get_text(strip=True)
                if text:
                    parts.append(f"\n{'#' * level} {text}")

            elif element.name == "p":
                text = element.get_text(strip=True)
                if text:
                    parts.append(f"\n{text}")

            elif element.name in ("li",):
                text = element.get_text(strip=True)
                if text:
                    parts.append(f"  • {text}")

            elif element.name == "a":
                text = element.get_text(strip=True)
                href = element.get("href", "")
                if text and href and not href.startswith(("#", "javascript:")):
                    if url and not href.startswith(("http://", "https://")):
                        href = urljoin(url, href)
                    parts.append(f"[{text}]({href})")

            elif element.name in ("pre", "code"):
                text = element.get_text()
                if text.strip():
                    parts.append(f"\n```\n{text.strip()}\n```")

            elif element.name == "blockquote":
                text = element.get_text(strip=True)
                if text:
                    parts.append(f"\n> {text}")

            elif element.name == "table":
                rows = element.find_all("tr")
                table_text: list[str] = []
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    row_text = " | ".join(c.get_text(strip=True) for c in cells)
                    if row_text.strip():
                        table_text.append(f"| {row_text} |")
                if table_text:
                    parts.append("\n" + "\n".join(table_text))

        result = "\n".join(parts).strip()

        # ── Fallback: if structured extraction yielded very little, use get_text ──
        if len(result) < 100:
            text = (target or soup).get_text(separator="\n")
            lines = (line.strip() for line in text.splitlines())
            result = "\n".join(line for line in lines if line)

        # Collapse excessive blank lines
        result = re.sub(r"\n{3,}", "\n\n", result)

        if len(result) > max_length:
            # Try to truncate at a sentence boundary
            truncated = result[:max_length]
            last_period = truncated.rfind(". ")
            if last_period > max_length * 0.8:
                truncated = truncated[: last_period + 1]
            result = truncated + "\n\n[... content truncated ...]"

        return result

    except Exception:
        # Last-resort fallback: regex strip tags
        text = re.sub(r"<[^>]+>", " ", html_content)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_length] + "..." if len(text) > max_length else text


# ── Rotating User-Agents ──
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

_MAX_RETRIES = 2
_RETRY_BACKOFF = 1.5  # seconds; multiplied each retry


def _build_headers() -> dict[str, str]:
    """Return realistic browser headers with a random User-Agent."""
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }


def _validate_url(url: str) -> str | None:
    """Return an error message if the URL is invalid, else None."""
    if not url or not url.strip():
        return "Error: No URL provided."

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        # Try auto-prefixing
        if "." in url and " " not in url:
            url = "https://" + url
        else:
            return f"Error: Invalid URL '{url}'. URLs must start with http:// or https://"

    parsed = urlparse(url)
    if not parsed.netloc:
        return f"Error: Invalid URL '{url}'. Could not determine the domain."

    return None


def _fetch_with_retries(url: str, session: requests.Session) -> requests.Response:
    """Fetch a URL with automatic retries on transient failures."""
    last_exception: Exception | None = None
    backoff = _RETRY_BACKOFF

    for attempt in range(_MAX_RETRIES + 1):
        if attempt > 0:
            time.sleep(backoff + random.uniform(0, 0.5))
            backoff *= 2
            # Rotate User-Agent on retry
            session.headers.update({"User-Agent": random.choice(_USER_AGENTS)})

        try:
            response = session.get(url, timeout=15, allow_redirects=True)

            # Retry on 429 (rate limit) or 5xx server errors
            if response.status_code == 429 or response.status_code >= 500:
                last_exception = requests.exceptions.HTTPError(response=response)
                if attempt < _MAX_RETRIES:
                    # Respect Retry-After header if present
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            time.sleep(min(float(retry_after), 10))
                        except ValueError:
                            pass
                    continue

            response.raise_for_status()
            return response

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as e:
            last_exception = e
            if attempt < _MAX_RETRIES:
                continue
            raise

    # If we exhausted retries on a 429/5xx, raise the last error
    if last_exception:
        raise last_exception
    raise requests.exceptions.RequestException(f"Failed to fetch {url} after {_MAX_RETRIES + 1} attempts")


@llm.tool
def browse_internet(url: str) -> str:
    """Browse a webpage and extract its text content.

    Fetches the given URL with browser-like headers and returns the readable
    text content of the page.  Automatically retries on transient server errors
    or rate limiting.

    Args:
        url: The URL to browse.  If the scheme is omitted, https:// is assumed.

    Returns:
        Structured text extracted from the page, or a human-readable error
        message starting with "Error:" if the page could not be fetched.
    """
    # ── Normalise URL ──
    url = url.strip()
    if url and not url.startswith(("http://", "https://")) and "." in url and " " not in url:
        url = "https://" + url

    validation_error = _validate_url(url)
    if validation_error:
        return validation_error

    session = requests.Session()
    session.headers.update(_build_headers())

    try:
        response = _fetch_with_retries(url, session)

        # Detect content type
        content_type = response.headers.get("Content-Type", "")
        if not any(ct in content_type for ct in ("text/html", "text/plain", "application/xhtml", "application/xml")):
            size = response.headers.get("Content-Length", "unknown")
            return (
                f"Error: The URL returned non-text content.\n"
                f"  Content-Type: {content_type}\n"
                f"  Size: {size} bytes\n"
                f"  URL: {url}\n"
                "Tip: This may be a PDF, image, or binary file."
            )

        # Detect near-empty responses
        if not response.text or len(response.text.strip()) < 20:
            return f"Error: The page at {url} returned an empty or near-empty response."

        # Detect encoding and re-decode if needed
        if response.encoding and response.encoding.lower() != "utf-8":
            response.encoding = response.apparent_encoding

        content = _extract_text(response.text, url=url)

        if not content or len(content.strip()) < 20:
            return (
                f"Error: Could not extract meaningful text from {url}. "
                "The page may rely on JavaScript to render content."
            )

        # Build a useful preamble
        final_url = response.url  # after redirects
        preamble = f"Content from: {final_url}"
        if final_url != url:
            preamble += f"  (redirected from {url})"

        return f"{preamble}\n{'─' * 60}\n\n{content}"

    except requests.exceptions.Timeout:
        return (
            f"Error: Request to {url} timed out after 15 seconds.\n"
            "Tip: The site may be slow or unresponsive. Try again later."
        )
    except requests.exceptions.TooManyRedirects:
        return (
            f"Error: Too many redirects when accessing {url}.\n"
            "Tip: The URL may be misconfigured or behind a redirect loop."
        )
    except requests.exceptions.ConnectionError:
        return (
            f"Error: Could not connect to {url}.\n"
            "Tip: Check that the domain exists and is spelled correctly."
        )
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        reason = e.response.reason if e.response is not None else "unknown"
        msg = f"Error: HTTP {status} ({reason}) for {url}."
        if status == 403:
            msg += "\nTip: The site is blocking automated access."
        elif status == 404:
            msg += "\nTip: The page was not found. Check the URL for typos."
        elif status == 429:
            msg += "\nTip: Rate limited. Wait before retrying."
        return msg
    except requests.exceptions.RequestException as e:
        return f"Error: Request failed for {url}: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error for {url}: {type(e).__name__}: {str(e)}"
    finally:
        session.close()