"""
Zoning Regulations Finder - Multi-State Support
Streamlit app for finding official zoning regulations using AI
"""
import streamlit as st
import os
from dotenv import load_dotenv

# Import modules
from config import STATES, DEFAULT_STATE
from state_fetcher import fetch_municipalities, get_municipality_term
from regulation_search import search_zoning_regulations
from llm_selector import select_best_pdf_with_llm
from rag_search import process_pdf_for_rag, search_rag, check_pdf_in_mongodb, get_chunks_from_mongodb, get_stored_municipalities, delete_municipality_chunks, inspect_stored_chunks

# Load environment variables
load_dotenv()


def main():
    st.set_page_config(page_title="Zoning Regulations Finder", page_icon="📋")

    st.title("🏘️ Zoning Regulations Finder")
    st.write("AI-powered search for official zoning regulations across the United States")

    # Get API keys
    api_key = os.getenv("FIRECRAWL_API_KEY", "")
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    reducto_key = os.getenv("REDUCTO_API_KEY", "")

    # API key input (if not in env)
    col1, col2, col3 = st.columns(3)

    with col1:
        if not api_key:
            api_key = st.text_input(
                "Enter your Firecrawl API Key",
                type="password",
                help="Get your API key from https://firecrawl.dev or set FIRECRAWL_API_KEY in .env file"
            )
        else:
            st.success("✓ Firecrawl API key loaded from .env")

    with col2:
        if not openrouter_key:
            openrouter_key = st.text_input(
                "Enter your OpenRouter API Key",
                type="password",
                help="Get your API key from https://openrouter.ai/keys or set OPENROUTER_API_KEY in .env file"
            )
        else:
            st.success("✓ OpenRouter API key loaded from .env")

    with col3:
        if not reducto_key:
            reducto_key = st.text_input(
                "Enter your Reducto API Key",
                type="password",
                help="Get your API key from https://reducto.ai or set REDUCTO_API_KEY in .env file"
            )
        else:
            st.success("✓ Reducto API key loaded from .env")

    # Check required API keys
    if not api_key:
        st.warning("Please enter your Firecrawl API key or set FIRECRAWL_API_KEY in .env file")
        st.info("Create a .env file with: FIRECRAWL_API_KEY=your_api_key_here")
        return

    if not openrouter_key:
        st.warning("Please enter your OpenRouter API key or set OPENROUTER_API_KEY in .env file")
        st.info("Get your API key from https://openrouter.ai/keys")
        return

    # Initialize session state for RAG
    if 'rag_chunks' not in st.session_state:
        st.session_state.rag_chunks = None
    if 'rag_pdf_url' not in st.session_state:
        st.session_state.rag_pdf_url = None
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'selected_pdf' not in st.session_state:
        st.session_state.selected_pdf = None

    st.divider()

    # State selection
    available_states = list(STATES.keys())
    selected_state = st.selectbox(
        "Select a State",
        options=available_states,
        index=available_states.index(DEFAULT_STATE) if DEFAULT_STATE in available_states else 0
    )

    municipality_term = get_municipality_term(selected_state)

    # Fetch municipalities for selected state
    with st.spinner(f"Loading {selected_state} {municipality_term}s..."):
        municipalities_dict = fetch_municipalities(selected_state, api_key)

    if not municipalities_dict:
        st.error(f"Failed to load {selected_state} {municipality_term}s. Please check your Firecrawl API key and try again.")
        return

    st.success(f"Loaded {len(municipalities_dict)} {selected_state} {municipality_term}s")

    # Municipality selection
    selected_municipality = st.selectbox(
        f"Select a {municipality_term.title()}",
        options=[""] + sorted(municipalities_dict.keys()),
        index=0
    )

    # Debug toggle
    show_debug = st.checkbox("Show debug information", value=False)

    # Search button
    if selected_municipality:
        if st.button("Search for Zoning Regulations", type="primary"):
            with st.spinner(f"Searching for {selected_municipality} zoning regulations..."):
                results = search_zoning_regulations(
                    selected_municipality,
                    selected_state,
                    api_key,
                    show_debug=show_debug
                )

                # Store results in session state
                st.session_state.search_results = results

                # Get AI selection and store it
                if results and isinstance(results, dict) and 'data' in results:
                    selected_pdf = select_best_pdf_with_llm(
                        selected_municipality,
                        selected_state,
                        results['data'],
                        openrouter_key
                    )
                    st.session_state.selected_pdf = selected_pdf

        # Display results from session state
        results = st.session_state.search_results

        if results and isinstance(results, dict) and 'data' in results:
            if show_debug:
                # Show debug info
                with st.expander("🔍 Debug Info", expanded=True):
                    # Show the main page that was scraped
                    main_page = results['data'][0] if results['data'] else None
                    if main_page and not main_page.get('is_pdf', False):
                        st.write(f"**Top search result (scraped):** {main_page['url']}")

                    # Show all links found
                    all_links = results['data'][1:] if len(results['data']) > 1 else []
                    if all_links:
                        st.write(f"**Found {len(all_links)} links on that page:**")
                        for idx, link in enumerate(all_links[:20], 1):  # Show first 20
                            link_text = link.get('link_text', 'No text')
                            url = link.get('url', '')
                            is_pdf = "📄 PDF" if link.get('is_pdf', False) else "🔗 Link"
                            score = link.get('relevance', 0)
                            st.text(f"{idx}. {is_pdf} [{score}pts] {link_text[:80]}")
                            st.text(f"   → {url[:100]}")
                        if len(all_links) > 20:
                            st.text(f"... and {len(all_links) - 20} more")

            # Show statistics
            pdf_count = sum(1 for r in results['data'] if r.get('is_pdf', False))
            st.info(f"Found {len(results['data'])} result(s) • {pdf_count} PDF(s) detected")

            # Get selected PDF from session state
            selected_pdf = st.session_state.selected_pdf

            # Show what was selected
            if selected_pdf and show_debug:
                with st.expander("🔍 Debug Info", expanded=True):
                    st.write("**🤖 AI Selected:**")
                    st.write(f"Link text: {selected_pdf.get('link_text', 'N/A')}")
                    st.write(f"URL: {selected_pdf.get('url', 'N/A')}")
                    st.write(f"Relevance score: {selected_pdf.get('relevance', 0)}")

            if selected_pdf:
                # Safety check
                if not selected_pdf.get('is_pdf', False):
                    st.warning("⚠️ Selected result may not be a PDF file")

                st.markdown("### 📄 Recommended Zoning Regulations")

                title = selected_pdf.get('title', 'Untitled')
                url = selected_pdf.get('url', '')

                # Display prominently
                st.markdown(f"**[{title}]({url})**")

                # RAG Search Feature
                st.markdown("---")
                st.markdown("### 🔍 Search This Document (RAG)")

                if not reducto_key:
                    st.info("💡 Enter your Reducto API key above to enable document search")
                else:
                    # Check if chunks are already in session state for this municipality
                    pdf_in_session = (
                        st.session_state.rag_chunks is not None and
                        st.session_state.rag_pdf_url == url
                    )

                    if pdf_in_session:
                        st.success(f"✓ Document ready ({len(st.session_state.rag_chunks)} chunks)")
                        # Debug: Show what's stored
                        if show_debug:
                            with st.expander("🔍 Inspect stored chunks"):
                                info = inspect_stored_chunks(selected_state, selected_municipality)
                                total = info.get('count', 0)
                                with_emb = info.get('with_embeddings', 0)
                                st.write(f"**Total chunks:** {total}")
                                st.write(f"**With embeddings:** {with_emb} ({100*with_emb//max(total,1)}%)")
                                for sample in info.get('samples', []):
                                    emb_status = "✓" if sample.get('has_embedding') else "✗"
                                    st.write(f"**Chunk {sample['chunk_index']}:** {sample['content_length']} chars | Embedding: {emb_status}")
                                    st.code(sample['content_preview'])
                    else:
                        # Check if this municipality was already processed (by state + municipality)
                        pdf_in_mongodb = check_pdf_in_mongodb(state=selected_state, municipality=selected_municipality)

                        if pdf_in_mongodb:
                            # Auto-load from MongoDB instead of re-processing
                            with st.spinner(f"Loading {selected_municipality} data from database..."):
                                chunks = get_chunks_from_mongodb(state=selected_state, municipality=selected_municipality)

                                # Check if chunks have valid content
                                valid_chunks = [c for c in chunks if c.get("content") and len(c.get("content", "")) > 10]

                                if valid_chunks:
                                    st.session_state.rag_chunks = chunks
                                    st.session_state.rag_pdf_url = url
                                    st.success(f"✓ Loaded {len(chunks)} chunks for {selected_municipality}, {selected_state} (cached)")
                                    st.rerun()
                                else:
                                    # Data exists but is empty/corrupted - offer to re-process
                                    st.warning(f"Cached data for {selected_municipality} appears empty or corrupted.")
                                    if st.button("🔄 Clear cache and re-process", type="secondary"):
                                        deleted = delete_municipality_chunks(selected_state, selected_municipality)
                                        st.info(f"Cleared {deleted} old chunks. Click 'Process PDF' to re-process.")
                                        st.rerun()
                        else:
                            # Need to process with Reducto
                            if st.button("📥 Process PDF for Search", type="secondary"):
                                # Download the PDF first (handles redirects)
                                from regulation_search import download_pdf_to_temp, get_redirect_url

                                temp_file_path = None

                                # Try regular download first
                                with st.spinner("Downloading PDF..."):
                                    temp_file_path = download_pdf_to_temp(url)

                                if temp_file_path:
                                    # Use the downloaded file, store with state/municipality
                                    st.success("✓ PDF downloaded successfully")
                                    chunks = process_pdf_for_rag(
                                        temp_file_path, reducto_key,
                                        storage_url=url,
                                        state=selected_state,
                                        municipality=selected_municipality,
                                        debug=show_debug
                                    )
                                    if chunks:
                                        st.session_state.rag_chunks = chunks
                                        st.session_state.rag_pdf_url = url
                                        st.rerun()
                                else:
                                    # If download fails, try to get redirect URL and use Reducto directly
                                    st.info("Trying to get redirect URL for Reducto...")
                                    redirect_url = get_redirect_url(url)

                                    if redirect_url and redirect_url != url:
                                        st.info(f"Found redirect URL: {redirect_url}")
                                        # Try Reducto with redirect URL, store with state/municipality
                                        chunks = process_pdf_for_rag(
                                            redirect_url, reducto_key,
                                            storage_url=url,
                                            state=selected_state,
                                            municipality=selected_municipality,
                                            debug=show_debug
                                        )
                                        if chunks:
                                            st.session_state.rag_chunks = chunks
                                            st.session_state.rag_pdf_url = url
                                            st.rerun()
                                    else:
                                        st.error("⚠️ Could not access PDF. The server is blocking automated requests.")

                    # Show search interface if document is processed
                    if st.session_state.rag_chunks and st.session_state.rag_pdf_url == url:
                        question = st.text_input(
                            "Ask a question about this document:",
                            placeholder="e.g., What are the setback requirements for residential zones?"
                        )

                        if question:
                            with st.spinner("Searching document..."):
                                answer = search_rag(
                                    question,
                                    st.session_state.rag_chunks,
                                    openrouter_key,
                                    debug=show_debug
                                )

                                if answer:
                                    st.markdown("**Answer:**")
                                    st.markdown(answer)

                st.divider()

            # Show all results in expandable section
            with st.expander("📋 View All Results", expanded=False):
                for idx, result in enumerate(results['data'], 1):
                    title = result.get('title', 'Untitled')
                    url = result.get('url', '')
                    is_pdf = result.get('is_pdf', False)

                    # Add indicator
                    indicator = "📄" if is_pdf else "🔗"

                    # Highlight selected
                    if selected_pdf and url == selected_pdf.get('url'):
                        st.markdown(f"{idx}. {indicator} **[{title}]({url})** ⭐")
                    else:
                        st.markdown(f"{idx}. {indicator} [{title}]({url})")
        else:
            if st.session_state.search_results is not None:
                st.warning("No results found")


if __name__ == "__main__":
    main()
