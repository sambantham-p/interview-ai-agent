from io import BytesIO

from pypdf import PdfWriter
from pypdf.annotations import Link

from app.core.pdf_links import (
    extract_pdf_link_targets,
    find_github_profile_url,
    is_github_profile_url,
)


def _pdf_with_links(*urls: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    for i, url in enumerate(urls):
        writer.add_annotation(
            page_number=0,
            annotation=Link(rect=(10, 10 + i * 20, 60, 25 + i * 20), url=url),
        )
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_extracts_link_targets_in_order_without_duplicates() -> None:
    pdf = _pdf_with_links(
        "https://github.com/sam",
        "https://linkedin.com/in/sam",
        "https://github.com/sam",
    )

    assert extract_pdf_link_targets(pdf) == [
        "https://github.com/sam",
        "https://linkedin.com/in/sam",
    ]


def test_ignores_non_http_links() -> None:
    assert extract_pdf_link_targets(_pdf_with_links("mailto:sam@example.com")) == []


def test_pdf_without_links_returns_empty_list() -> None:
    assert extract_pdf_link_targets(_pdf_with_links()) == []


def test_unreadable_pdf_returns_empty_list_instead_of_raising() -> None:
    assert extract_pdf_link_targets(b"not a pdf at all") == []


def test_is_github_profile_url() -> None:
    assert is_github_profile_url("https://github.com/sam")
    assert is_github_profile_url("https://www.github.com/sam/")
    assert not is_github_profile_url("github.com")
    assert not is_github_profile_url("https://github.com/sam/repo")
    assert not is_github_profile_url(None)


def test_find_github_profile_url_prefers_a_profile_link() -> None:
    links = ["https://github.com/sam/project", "https://github.com/sam"]

    assert find_github_profile_url(links) == "https://github.com/sam"


def test_find_github_profile_url_falls_back_to_repo_owner() -> None:
    assert (
        find_github_profile_url(["https://x.com/a", "https://github.com/sam/project"])
        == "https://github.com/sam"
    )


def test_find_github_profile_url_returns_none_without_github_links() -> None:
    assert find_github_profile_url(["https://linkedin.com/in/sam"]) is None
