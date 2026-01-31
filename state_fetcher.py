"""
Module for fetching municipalities (towns/cities) from state government sources
"""
import re
import streamlit as st
from firecrawl import FirecrawlApp
from config import STATES


@st.cache_data
def fetch_municipalities(state_name, _api_key):
    """
    Fetch municipalities and their official websites for a given state

    Args:
        state_name: Name of the state (e.g., "Connecticut")
        _api_key: Firecrawl API key (prefixed with _ to avoid caching issues)

    Returns:
        dict: Mapping of municipality name to website URL (or None if no website found)
    """
    if state_name not in STATES:
        st.error(f"State '{state_name}' not configured")
        return {}

    state_config = STATES[state_name]
    source_url = state_config.get('source_url')

    # If no source URL, can't fetch municipalities
    if not source_url:
        st.error(f"No source URL configured for {state_name}")
        return {}

    try:
        app = FirecrawlApp(api_key=_api_key)

        # Use Firecrawl to scrape the page
        result = app.scrape(source_url, formats=['links', 'markdown'])

        if result:
            # Firecrawl returns a Document object, access attributes directly
            links = getattr(result, 'links', None)
            markdown = getattr(result, 'markdown', '')

            if links:
                municipality_websites = {}
                discovered_municipalities = set()

                # First, extract town names from markdown if available
                if markdown:
                    # Parse markdown to find town names
                    # They appear as links in the format: [TownName](url)
                    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', markdown)
                    for text, url in markdown_links:
                        text = text.strip()
                        # Filter out single letters (A, B, C headers) and generic links
                        if (len(text) > 2 and
                            len(text) < 50 and
                            text[0].isupper() and
                            text.lower() not in ['home', 'about', 'contact', 'services', 'government']):
                            discovered_municipalities.add(text)
                            municipality_websites[text] = url

                # Also extract from links object
                for link_obj in links:
                    # Get URL
                    try:
                        if hasattr(link_obj, 'url'):
                            link_url = link_obj.url
                        else:
                            link_url = str(link_obj)
                    except:
                        continue

                    # Only process .gov, .org, .us links
                    if not any(ext in str(link_url).lower() for ext in ['.gov', '.org', '.us']):
                        continue

                    # Try to get link text
                    link_text = None
                    try:
                        # Try object attributes
                        for attr in ['text', 'title', 'name', 'label']:
                            if hasattr(link_obj, attr):
                                val = getattr(link_obj, attr, None)
                                if val:
                                    link_text = str(val)
                                    break

                        # Try dict access
                        if not link_text and hasattr(link_obj, '__getitem__'):
                            link_text = link_obj.get('text') or link_obj.get('title')
                    except:
                        pass

                    if link_text:
                        cleaned_text = re.sub(r'^(Town of |City of |Borough of )', '', link_text, flags=re.IGNORECASE)
                        cleaned_text = cleaned_text.strip()

                        if (cleaned_text and
                            len(cleaned_text) > 2 and
                            len(cleaned_text) < 50 and
                            cleaned_text[0].isupper() and
                            cleaned_text.lower() not in ['home', 'about', 'contact', 'services', 'government']):
                            discovered_municipalities.add(cleaned_text)
                            municipality_websites[cleaned_text] = str(link_url)

                # Return all discovered municipalities
                if discovered_municipalities:
                    return {muni: municipality_websites.get(muni, None)
                           for muni in sorted(discovered_municipalities)}
            else:
                st.warning("No links found in the scraped result")

    except Exception as e:
        st.error(f"Failed to fetch from {source_url} with Firecrawl: {e}")
        import traceback
        st.code(traceback.format_exc())

    # No fallback - return empty dict
    return {}


def get_municipality_term(state_name):
    """
    Get the term used for municipalities in a given state

    Args:
        state_name: Name of the state

    Returns:
        str: "town", "city", or "municipality"
    """
    if state_name in STATES:
        return STATES[state_name].get('municipality_term', 'municipality')
    return 'municipality'


def get_state_abbreviation(state_name):
    """
    Get the abbreviation for a given state

    Args:
        state_name: Name of the state

    Returns:
        str: State abbreviation (e.g., "CT")
    """
    if state_name in STATES:
        return STATES[state_name].get('abbreviation', '')
    return ''
