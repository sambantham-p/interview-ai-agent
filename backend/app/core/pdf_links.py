"""Reads hyperlink targets out of a PDF's link annotations.

A hyperlink's target URL lives in the page's annotations, not in the
page's visible text, so a model that only sees the rendered page can read
the link's label ("GitHub") but never where it points.
"""

import re
from io import BytesIO

import structlog
from pypdf import PdfReader

logger = structlog.get_logger(__name__)

_GITHUB_URL = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[^/?#\s]+)(?P<rest>/[^?#\s]*)?",
    re.IGNORECASE,
)


def extract_pdf_link_targets(file_bytes: bytes) -> list[str]:
    """Every distinct http(s) link target in the PDF, in page order.

    Never raises: an unreadable or unusual PDF just yields no links, so
    link extraction can only add information, never fail an upload.
    """
    try:
        reader = PdfReader(BytesIO(file_bytes))
        targets: list[str] = []
        for page in reader.pages:
            for annotation in page.get("/Annots") or []:
                action = annotation.get_object().get("/A")
                uri = action.get_object().get("/URI") if action else None
                if (
                    isinstance(uri, str)
                    and uri.lower().startswith(("http://", "https://"))
                    and uri not in targets
                ):
                    targets.append(uri)
        return targets
    except Exception:  # noqa: BLE001 - best-effort enrichment, see docstring
        logger.warning("resume.pdf_links.unreadable")
        return []


def is_github_profile_url(url: str | None) -> bool:
    """True for a real https://github.com/<user> profile URL."""
    if not url:
        return False
    match = _GITHUB_URL.match(url.strip())
    return match is not None and not (match.group("rest") or "").strip("/")


def find_github_profile_url(links: list[str]) -> str | None:
    """The candidate's GitHub profile URL from the PDF's links: the first
    profile link, else the owner of the first repository link.
    """
    owners = []
    for link in links:
        match = _GITHUB_URL.match(link)
        if match is None:
            continue
        owner_url = f"https://github.com/{match.group('owner')}"
        if is_github_profile_url(link):
            return owner_url
        owners.append(owner_url)
    return owners[0] if owners else None
