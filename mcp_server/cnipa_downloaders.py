#!/usr/bin/env python3
"""
CNIPA (China) Legal Document Downloaders

Downloads English-language patent law documents for the China National
Intellectual Property Administration (CNIPA) for indexing in the RAG pipeline.

Documents:
    - Patent Law of the People's Republic of China (4th revision, 2020 / in force 2021)
    - Implementing Regulations of the Patent Law
    - Guidelines for Patent Examination

Sourcing notes:
    - Patent Law and Implementing Regulations have official English translations
      published on WIPO Lex.
    - The Guidelines for Patent Examination are primarily published in Chinese by
      CNIPA. Where an English translation PDF is not available, users can drop a
      locally-translated copy at pdfs/cn_examination_guidelines.pdf and the
      indexer will pick it up automatically.

If a download URL changes, set the file manually in pdfs/ — the indexer
checks for file presence, not download success.
"""

import sys
from pathlib import Path

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from logging_config import get_logger

    logger = get_logger()
    LOGGING_AVAILABLE = True
except ImportError:
    logger = None
    LOGGING_AVAILABLE = False


def _log_info(msg: str, **kwargs):
    if LOGGING_AVAILABLE and logger:
        logger.info(msg, extra=kwargs)
    else:
        print(f"[INFO] {msg}", file=sys.stderr)


def _log_error(msg: str, **kwargs):
    if LOGGING_AVAILABLE and logger:
        logger.error(msg, extra=kwargs)
    else:
        print(f"[ERROR] {msg}", file=sys.stderr)


# =============================================================================
# Download URLs (verify before relying on them in production; users may
# manually drop the files in pdfs/ if a URL is unreachable)
# =============================================================================

# Patent Law of the PRC (4th revision, in force June 1, 2021)
# English translation hosted on WIPO Lex.
CN_PATENT_LAW_URL = "https://www.wipo.int/wipolex/en/text/591617"

# Implementing Regulations of the Patent Law of the PRC
# English translation hosted on WIPO Lex.
CN_REGULATIONS_URL = "https://www.wipo.int/wipolex/en/text/586855"

# Guidelines for Patent Examination — CNIPA publishes the Chinese edition only.
# When an EN translation is unavailable, users should place a translated PDF at
# pdfs/cn_examination_guidelines.pdf. Left as an empty string to signal that
# automatic download is not attempted by default.
CN_GUIDELINES_URL = ""

# File names for stored documents
CN_PATENT_LAW_FILE = "cn_patent_law.pdf"
CN_REGULATIONS_FILE = "cn_implementing_regulations.pdf"
CN_GUIDELINES_FILE = "cn_examination_guidelines.pdf"


def _download_file(url: str, dest_path: Path, description: str, timeout: int = 120) -> bool:
    """Download a file with progress reporting (mirrors the helper in epo_downloaders)."""
    if not REQUESTS_AVAILABLE:
        _log_error(f"Cannot download {description}: requests library not available")
        return False

    if not url:
        _log_info(f"{description}: no download URL configured — place the file manually at {dest_path}")
        return False

    if dest_path.exists():
        _log_info(f"{description} already exists at {dest_path}")
        return True

    _log_info(f"Downloading {description}...", url=url)

    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)

        size_mb = downloaded / (1024 * 1024)
        _log_info(f"Downloaded {description} ({size_mb:.1f} MB)")
        return True

    except Exception as e:
        _log_error(f"Failed to download {description}: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def download_cn_patent_law(dest_dir: Path) -> bool:
    """Download Patent Law of the PRC (English translation)."""
    return _download_file(
        url=CN_PATENT_LAW_URL,
        dest_path=dest_dir / CN_PATENT_LAW_FILE,
        description="Patent Law of the People's Republic of China",
    )


def download_cn_regulations(dest_dir: Path) -> bool:
    """Download Implementing Regulations of the Patent Law of the PRC."""
    return _download_file(
        url=CN_REGULATIONS_URL,
        dest_path=dest_dir / CN_REGULATIONS_FILE,
        description="Implementing Regulations of the Patent Law (PRC)",
    )


def download_cn_examination_guidelines(dest_dir: Path) -> bool:
    """Download CNIPA Guidelines for Patent Examination if a URL is configured.

    Returns True when the file is present (downloaded or already on disk),
    False when no URL is configured and the file is absent.
    """
    dest = dest_dir / CN_GUIDELINES_FILE
    if dest.exists():
        _log_info(f"CN Examination Guidelines already exist at {dest}")
        return True
    if not CN_GUIDELINES_URL:
        _log_info(
            "CN Examination Guidelines: no public English PDF URL configured. "
            f"Place a translated copy at {dest} to index."
        )
        return False
    return _download_file(
        url=CN_GUIDELINES_URL,
        dest_path=dest,
        description="CNIPA Guidelines for Patent Examination",
    )


def download_all_cn_documents(dest_dir: Path) -> dict[str, bool]:
    """Download all CN-related legal documents.

    Returns:
        Dict mapping document name to download success.
    """
    return {
        "cn_patent_law": download_cn_patent_law(dest_dir),
        "cn_regulations": download_cn_regulations(dest_dir),
        "cn_guidelines": download_cn_examination_guidelines(dest_dir),
    }


def check_cnipa_sources(dest_dir: Path) -> dict[str, bool]:
    """Check which CNIPA source documents are available on disk."""
    return {
        "cn_patent_law": (dest_dir / CN_PATENT_LAW_FILE).exists(),
        "cn_regulations": (dest_dir / CN_REGULATIONS_FILE).exists(),
        "cn_guidelines": (dest_dir / CN_GUIDELINES_FILE).exists(),
    }
