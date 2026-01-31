"""
Module for searching zoning regulations using Firecrawl
"""
import re
import os
import tempfile
import requests
import streamlit as st
from urllib.parse import urlparse
from firecrawl import FirecrawlApp
from config import (
    ZONING_KEYWORDS,
    PDF_DIRECTORY_PATTERNS,
    WEB_PAGE_EXTENSIONS,
    ZONING_FILE_KEYWORDS,
    SCRAPE_TIMEOUT,
    SCORE_LINK_TEXT_KEYWORD,
    SCORE_URL_KEYWORD,
    SCORE_IS_PDF,
    SCORE_RECENT_YEAR,
    PENALTY_UNWANTED_TERMS,
    PENALTY_UNWANTED_URL,
    UNWANTED_TERMS
)


# --------------------------------------------------
# PDF Download Utilities
# --------------------------------------------------

def get_redirect_url(url: str, timeout: int = 10) -> str:
    """
    Try to get the final redirect URL without triggering bot detection.
    Returns the redirect URL or None if can't determine.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/pdf,*/*",
        }
        
        # Try HEAD request first (lighter, might not trigger bot detection)
        resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        
        # If we got a successful redirect, return the final URL
        if resp.status_code == 200:
            return resp.url
        
        # If HEAD failed, try GET with streaming to minimize data transfer
        if resp.status_code in [403, 401]:
            resp = requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True)
            # Close connection immediately
            resp.close()
            
            if resp.status_code == 200:
                return resp.url
        
        return None
        
    except Exception:
        return None


def download_pdf_to_temp(url: str, timeout: int = 30) -> str:
    """
    Download a PDF from URL and save to temporary file.
    Returns the temp file path if successful, None otherwise.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/pdf,application/octet-stream,*/*",
    }
    
    try:
        # Download directly (requests follows redirects automatically)
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        content = response.content
        
        # Check if it's a PDF
        if content[:4] == b'%PDF':
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(content)
                return tmp_file.name
        
        return None
        
    except Exception:
        return None


def download_pdf_with_firecrawl(url: str, api_key: str) -> str:
    """
    Use Firecrawl to download PDF from bot-protected pages.
    Firecrawl can handle JavaScript challenges that block regular requests.
    Returns the temp file path if successful, None otherwise.
    """
    try:
        app = FirecrawlApp(api_key=api_key)
        
        # Try to scrape with raw content to get PDF data
        result = app.scrape(url, formats=['markdown', 'links'], timeout=30000)
        
        if not result:
            return None
        
        # Try to find PDF link in markdown
        markdown = getattr(result, 'markdown', '')
        if markdown:
            pdf_links = re.findall(r'\[([^\]]+)\]\(([^)]+\.pdf[^)]*)\)', markdown, re.IGNORECASE)
            if pdf_links:
                for _, pdf_url in pdf_links:
                    # Try direct download of the PDF link
                    temp_path = download_pdf_to_temp(pdf_url)
                    if temp_path:
                        return temp_path
        
        # Try to find PDF link in links
        links = getattr(result, 'links', [])
        if links:
            for link_obj in links:
                link_url = None
                if hasattr(link_obj, 'url'):
                    link_url = link_obj.url
                elif hasattr(link_obj, 'href'):
                    link_url = link_obj.href
                elif isinstance(link_obj, str):
                    link_url = link_obj
                
                if link_url and '.pdf' in link_url.lower():
                    temp_path = download_pdf_to_temp(link_url)
                    if temp_path:
                        return temp_path
        
        return None
        
    except Exception as e:
        return None


def is_likely_pdf(url, link_text=None):
    """
    Detect if a URL is likely a PDF document

    Args:
        url: URL to check
        link_text: Optional link text/anchor text for additional context

    Returns:
        bool: True if likely a PDF, False otherwise
    """
    url_lower = url.lower()

    # Remove query parameters for extension checking
    url_without_query = url_lower.split('?')[0].split('#')[0]

    # Direct PDF extension - always a PDF
    if url_without_query.endswith('.pdf'):
        return True

    # Check for common download/file handlers and document centers
    download_patterns = ['/download', '/file', '/document', '/attachment', 'getfile', 'viewfile', '/documentcenter/view', '/documentcenter']
    if any(pattern in url_lower for pattern in download_patterns):
        # If link text has zoning keywords, very likely a PDF (don't require "pdf" in text)
        if link_text:
            link_text_lower = link_text.lower()
            # Check for zoning keywords - if present, assume it's a PDF
            if any(keyword in link_text_lower for keyword in ZONING_FILE_KEYWORDS):
                return True
            # Also check if "pdf" is mentioned
            if 'pdf' in link_text_lower:
                return True
        # For DocumentCenter specifically, be more lenient
        if '/documentcenter' in url_lower:
            return True

    # Exclude obvious web pages
    if any(ext in url_lower for ext in WEB_PAGE_EXTENSIONS):
        return False

    # Get the last part of the URL path
    path_parts = url_lower.split('/')
    if not path_parts:
        return False

    last_part = path_parts[-1]

    # If last part is empty or looks like a directory, not a PDF
    if not last_part or last_part in ['', 'index', 'default']:
        return False

    # Check if it's in a document hosting directory
    is_in_files_dir = any(pattern in url_lower for pattern in PDF_DIRECTORY_PATTERNS)

    # If in files directory AND has document-like characteristics
    if is_in_files_dir:
        # Must have dashes, underscores, or contain 'pdf' in the filename
        has_file_pattern = ('-' in last_part or '_' in last_part or 'pdf' in last_part)
        # Must contain zoning-related keywords in the filename
        has_zoning_keywords = any(keyword in last_part for keyword in ZONING_FILE_KEYWORDS)

        if has_file_pattern and has_zoning_keywords:
            # Additional check: filename should be substantial (not just a short slug)
            if len(last_part) > 8:  # e.g., "zoning-regulations-updated-10-18-25-edit"
                return True

    return False


def search_zoning_regulations(municipality_name, state_name, api_key, show_debug=False):
    """
    Search for zoning regulations for a specific municipality

    Two-step approach:
    1. Search for zoning regulations page
    2. Crawl that page to find PDF links

    Args:
        municipality_name: Name of the municipality (town/city)
        state_name: Name of the state
        api_key: Firecrawl API key
        show_debug: Whether to show debug information (default: False)

    Returns:
        dict: Search results with 'data' key containing list of results
    """
    try:
        app = FirecrawlApp(api_key=api_key)

        # Step 1: Search for the zoning regulations page
        search_query = f"{municipality_name} {state_name} Zoning Regulations 2025"

        search_results = app.search(search_query, limit=5)

        if not search_results:
            st.warning("No search results found")
            return None

        # The search results have .web, .news, .images attributes
        # We want the web results
        web_results = getattr(search_results, 'web', None)

        if not web_results:
            st.warning("No web search results found")
            return None

        # Get the first result
        first_result = web_results[0]
        target_url = getattr(first_result, 'url', None) or first_result.get('url', '')

        if not target_url:
            st.warning("No URL found in search results.")
            return None

        # Get the title from first result (handle both dict and object)
        result_title = getattr(first_result, 'title', None) or first_result.get('title', f"{municipality_name} Zoning Regulations")

        # If it's already a PDF, return it (will download after LLM selection)
        if is_likely_pdf(target_url):
            return {'data': [{
                'url': target_url,
                'title': result_title,
                'is_pdf': True
            }]}

        # Step 2: Scrape the page to find PDF links
        scrape_result = app.scrape(
            target_url,
            formats=['links', 'markdown', 'html'],
            timeout=SCRAPE_TIMEOUT,
            only_main_content=False  # Include sidebars and all page content
        )

        all_results = []

        # Add the main page
        all_results.append({
            'url': target_url,
            'title': result_title,
            'is_pdf': False
        })

        if scrape_result:
            links = getattr(scrape_result, 'links', [])
            markdown = getattr(scrape_result, 'markdown', '')
            html = getattr(scrape_result, 'html', '')

            # DEBUG: Show what we got from Firecrawl
            if show_debug:
                st.write("**🔍 Debug: Firecrawl returned:**")
                st.write(f"- {len(links)} structured links")
                st.write(f"- {len(markdown)} chars of markdown")
                st.write(f"- {len(html)} chars of html")

                # Show a sample of markdown to see what's in there
                if markdown:
                    with st.expander("View Markdown Sample (first 3000 chars)", expanded=False):
                        st.code(markdown[:3000])

                # Look for the specific link in markdown
                if 'zoning' in markdown.lower() and 'regulation' in markdown.lower():
                    st.write("✓ Markdown contains 'zoning' and 'regulation' keywords")

                    # Show ALL lines with zoning/regulation
                    with st.expander("🔍 Lines with 'zoning' or 'regulation' in markdown", expanded=True):
                        for line_num, line in enumerate(markdown.split('\n'), 1):
                            if 'zoning' in line.lower() or 'regulation' in line.lower():
                                st.text(f"{line_num}: {line[:300]}")

                if 'documentcenter' in markdown.lower():
                    st.write("✓ Markdown contains 'documentcenter'")
                    # Show lines with documentcenter
                    with st.expander("DocumentCenter links in markdown", expanded=False):
                        for line in markdown.split('\n'):
                            if 'documentcenter' in line.lower():
                                st.text(line[:200])

            # Store ALL links with their text: {url: link_text}
            all_links_dict = {}

            # First, process Firecrawl's structured links - GET EVERYTHING
            if show_debug:
                st.write(f"**DEBUG: Processing {len(links)} Firecrawl links**")

            if links:
                for idx, link_obj in enumerate(links):
                    try:
                        # Get URL
                        if hasattr(link_obj, 'url'):
                            link_url = link_obj.url
                        elif hasattr(link_obj, 'href'):
                            link_url = link_obj.href
                        else:
                            link_url = str(link_obj)

                        # Get link text - try multiple attributes
                        link_text = None
                        for attr in ['text', 'title', 'name', 'label', 'anchor_text']:
                            if hasattr(link_obj, attr):
                                val = getattr(link_obj, attr, None)
                                if val:
                                    link_text = str(val).strip()
                                    break

                        # Also try dict access
                        if not link_text and hasattr(link_obj, 'get'):
                            link_text = link_obj.get('text') or link_obj.get('title') or link_obj.get('anchor_text')

                        # ADD EVERY LINK, even without text
                        if link_url:
                            all_links_dict[link_url] = link_text or "No text"

                            # Debug: show links with zoning/regulation in them
                            if show_debug and link_text and ('zoning' in link_text.lower() or 'regulation' in link_text.lower()):
                                st.write(f"  Found: {link_text[:80]} -> {link_url[:80]}")
                    except Exception as e:
                        if show_debug:
                            st.write(f"  Error processing link {idx}: {e}")
                        continue

            # Also extract from markdown and HTML - GET EVERYTHING
            additional_links = {}

            # Extract ALL links from markdown
            if markdown:
                md_all_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', markdown, re.IGNORECASE)
                if show_debug:
                    st.write(f"**DEBUG: Found {len(md_all_links)} links in markdown**")
                for text, url in md_all_links:
                    additional_links[url] = text.strip()
                    # Debug: show links with zoning/regulation
                    if show_debug and ('zoning' in text.lower() or 'regulation' in text.lower()):
                        st.write(f"  Markdown: {text[:80]} -> {url[:80]}")

            # Extract ALL links from HTML
            if html:
                anchor_pattern = r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
                all_anchor_matches = re.findall(anchor_pattern, html, re.IGNORECASE | re.DOTALL)
                if show_debug:
                    st.write(f"**DEBUG: Found {len(all_anchor_matches)} links in HTML**")

                for url, inner_html in all_anchor_matches:
                    # Extract text from inner HTML (strip all tags)
                    text = re.sub(r'<[^>]+>', '', inner_html)
                    clean_text = re.sub(r'\s+', ' ', text).strip()

                    if clean_text:
                        additional_links[url] = clean_text
                        # Debug: show links with zoning/regulation
                        if show_debug and ('zoning' in clean_text.lower() or 'regulation' in clean_text.lower()):
                            st.write(f"  HTML: {clean_text[:80]} -> {url[:80]}")

            # Merge additional links with Firecrawl links (additional takes precedence if same URL)
            for url, text in additional_links.items():
                if url not in all_links_dict or text:  # Override if we have text
                    all_links_dict[url] = text

            # Process all collected links
            for link_url, link_text in all_links_dict.items():
                # Make absolute URL if needed
                if link_url.startswith('http'):
                    full_url = link_url
                elif link_url.startswith('/'):
                    # Relative to domain root
                    parsed = urlparse(target_url)
                    full_url = f"{parsed.scheme}://{parsed.netloc}{link_url}"
                else:
                    # Relative to current page
                    base_url = target_url.rsplit('/', 1)[0]
                    full_url = f"{base_url}/{link_url}"

                # Score this link based on relevance
                url_lower = full_url.lower()

                # Calculate relevance score
                relevance_score = 0

                # VERY HIGH priority: link text contains zoning keywords
                if link_text:
                    link_text_lower = link_text.lower()
                    for keyword in ZONING_KEYWORDS:
                        if keyword in link_text_lower:
                            relevance_score += SCORE_LINK_TEXT_KEYWORD

                    # PENALTY: Avoid summaries, proposed changes, amendments
                    for term in UNWANTED_TERMS:
                        if term in link_text_lower:
                            relevance_score += PENALTY_UNWANTED_TERMS

                # High priority: URL contains zoning keywords
                for keyword in ZONING_KEYWORDS:
                    if keyword in url_lower:
                        relevance_score += SCORE_URL_KEYWORD

                # PENALTY: Avoid summaries, proposed changes, amendments in URL
                for term in UNWANTED_TERMS:
                    if term in url_lower:
                        relevance_score += PENALTY_UNWANTED_URL

                # Check if it's a PDF using improved detection (pass link text for context)
                is_pdf = is_likely_pdf(full_url, link_text)

                # Medium priority: is a PDF or document
                if is_pdf or 'file' in url_lower or 'document' in url_lower:
                    relevance_score += SCORE_IS_PDF

                # Bonus: contains year indicators (2024, 2025, etc.)
                if any(year in url_lower for year in ['2025', '2024', '25', '24']):
                    relevance_score += SCORE_RECENT_YEAR

                # Determine best title to display
                if link_text:
                    display_title = link_text
                else:
                    display_title = full_url.split('/')[-1]

                all_results.append({
                    'url': full_url,
                    'title': display_title,
                    'link_text': link_text,  # Include for LLM analysis
                    'is_pdf': is_pdf,
                    'relevance': relevance_score
                })

        # Sort by relevance score (highest first)
        all_results.sort(key=lambda x: x.get('relevance', 0), reverse=True)

        return {'data': all_results}

    except Exception as e:
        st.error(f"Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None
