"""
Zoning Regulations Finder - Simplified UI
Streamlit app for finding official zoning regulations using AI
"""
import streamlit as st
import os
from dotenv import load_dotenv

# Import modules
from config import STATES
from state_fetcher import fetch_municipalities
from regulation_search import search_zoning_regulations, download_pdf_to_temp, get_redirect_url
from llm_selector import select_best_pdf_with_llm
from rag_search import (
    process_pdf_for_rag, search_rag, check_pdf_in_mongodb,
    get_chunks_from_mongodb, delete_municipality_chunks,
    generate_missing_embeddings, search_parcel_data, get_available_towns
)

# Load environment variables
load_dotenv()


def initialize_session_state():
    """Initialize all session state variables."""
    defaults = {
        'rag_chunks': None,
        'rag_pdf_url': None,
        'selected_state': None,
        'selected_municipality': None,
        'municipalities_dict': None,
        'is_ready': False,
        'status_message': '',
        'processing': False,
        'pdf_title': None,
        'available_towns': None  # Cache for towns only
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_api_keys():
    """Get API keys from environment."""
    return {
        'firecrawl': os.getenv("FIRECRAWL_API_KEY", ""),
        'openrouter': os.getenv("OPENROUTER_API_KEY", ""),
        'reducto': os.getenv("REDUCTO_API_KEY", ""),
    }


def prepare_municipality_data(state: str, municipality: str, api_keys: dict):
    """
    Prepare all data needed for RAG search.
    Returns True if ready, False if failed.
    """
    # Check if already cached in MongoDB
    if check_pdf_in_mongodb(state=state, municipality=municipality):
        st.session_state.status_message = "Loading cached data..."
        chunks = get_chunks_from_mongodb(state=state, municipality=municipality)

        # Validate chunks
        valid_chunks = [c for c in chunks if c.get("content") and len(c.get("content", "")) > 10]
        if valid_chunks:
            st.session_state.rag_chunks = chunks
            st.session_state.is_ready = True
            st.session_state.status_message = f"Ready ({len(chunks)} chunks loaded from cache)"
            return True
        else:
            # Corrupted cache - clear it
            delete_municipality_chunks(state, municipality)

    # Need to search and process
    st.session_state.status_message = "Searching for zoning regulations..."

    # Search for zoning regulations
    results = search_zoning_regulations(
        municipality, state, api_keys['firecrawl']
    )

    if not results or not isinstance(results, dict) or 'data' not in results:
        st.session_state.status_message = "No zoning regulations found"
        return False

    # Use LLM to select best PDF
    st.session_state.status_message = "Selecting best document..."
    selected_pdf = select_best_pdf_with_llm(
        municipality, state, results['data'], api_keys['openrouter']
    )

    if not selected_pdf:
        st.session_state.status_message = "Could not find a suitable document"
        return False

    url = selected_pdf.get('url', '')
    st.session_state.pdf_title = selected_pdf.get('title', 'Zoning Regulations')
    st.session_state.rag_pdf_url = url

    # Check if Reducto key is available
    if not api_keys['reducto']:
        st.session_state.status_message = "Reducto API key required for document processing"
        return False

    # Download and process PDF
    st.session_state.status_message = "Downloading document..."
    temp_file_path = download_pdf_to_temp(url)

    if temp_file_path:
        st.session_state.status_message = "Processing document (this may take a moment)..."
        chunks = process_pdf_for_rag(
            temp_file_path, api_keys['reducto'],
            storage_url=url,
            state=state,
            municipality=municipality
        )
    else:
        # Try redirect URL
        st.session_state.status_message = "Trying alternate download method..."
        redirect_url = get_redirect_url(url)

        if redirect_url and redirect_url != url:
            chunks = process_pdf_for_rag(
                redirect_url, api_keys['reducto'],
                storage_url=url,
                state=state,
                municipality=municipality
            )
        else:
            st.session_state.status_message = "Could not access document"
            return False

    if chunks:
        st.session_state.rag_chunks = chunks
        st.session_state.is_ready = True
        st.session_state.status_message = f"Ready ({len(chunks)} chunks)"
        return True

    st.session_state.status_message = "Failed to process document"
    return False


def main():
    st.set_page_config(
        page_title="Zoning Regulations Finder",
        page_icon="🏘️",
        layout="centered"
    )

    initialize_session_state()
    api_keys = get_api_keys()

    # Check for required API keys
    missing_keys = []
    if not api_keys['firecrawl']:
        missing_keys.append("FIRECRAWL_API_KEY")
    if not api_keys['openrouter']:
        missing_keys.append("OPENROUTER_API_KEY")
    if not api_keys['reducto']:
        missing_keys.append("REDUCTO_API_KEY")

    if missing_keys:
        st.error(f"Missing API keys in .env file: {', '.join(missing_keys)}")
        st.info("Create a .env file with your API keys")
        return

    # Title
    st.title("🏘️ Zoning Regulations & Property Finder")

    # Search mode selector
    st.markdown("### Search Mode")
    search_mode = st.radio(
        "Choose what to search:",
        ["Zoning Regulations", "Property/Parcel Data"],
        horizontal=True
    )

    if search_mode == "Property/Parcel Data":
        # Parcel Search UI
        st.markdown("### Property Search")
        st.markdown("Search Connecticut property and parcel data using vector search")
        
        # Load town data with caching (no counts for speed)
        if st.session_state.available_towns is None:
            with st.spinner("Loading towns..."):
                st.session_state.available_towns = get_available_towns()
        
        available_towns = st.session_state.available_towns
        
        # Town selector
        st.markdown("#### Select Town")
        
        # Simple dropdown without counts (much faster)
        parcel_town = st.selectbox(
            "Choose a town to search:",
            options=available_towns,
            help="Vector search will find properties in this town"
        )
        
        selected_town = parcel_town
        
        question = st.text_area(
            "Ask about properties:",
            placeholder="e.g., Find waterfront properties, Show 4 bedroom colonials, What are commercial properties?",
            key="parcel_question"
        )
        
        if question and st.button("🔍 Search Properties"):
            with st.spinner("Searching property data..."):
                answer = search_parcel_data(
                    question,
                    api_keys['openrouter'],
                    town=selected_town
                )
            
            if answer:
                st.markdown("### Property Search Results")
                st.markdown(answer)
        
        return  # Exit early for parcel search mode

    # Debug toggle in sidebar
    with st.sidebar:
        if st.session_state.pdf_title:
            st.markdown("---")
            st.markdown(f"**Document:** {st.session_state.pdf_title}")
        if st.session_state.rag_pdf_url:
            st.markdown(f"[View PDF]({st.session_state.rag_pdf_url})")

        # Clear cache button
        if st.session_state.selected_state and st.session_state.selected_municipality:
            st.markdown("---")
            if st.button("Clear cached data"):
                deleted = delete_municipality_chunks(
                    st.session_state.selected_state,
                    st.session_state.selected_municipality
                )
                st.session_state.rag_chunks = None
                st.session_state.is_ready = False
                st.session_state.status_message = f"Cleared {deleted} chunks"
                st.rerun()
        
        # Generate missing embeddings button
        st.markdown("---")
        if st.button("Generate missing embeddings"):
            with st.spinner("Generating missing embeddings..."):
                updated = generate_missing_embeddings(
                    st.session_state.selected_state,
                    st.session_state.selected_municipality
                )
                st.success(f"Generated embeddings for {updated} chunks")

    # State and Municipality selection (only for Zoning Regulations)
    if search_mode == "Zoning Regulations":
        st.markdown("### Select Location for Zoning Regulations")
        
        col1, col2 = st.columns(2)

        available_states = list(STATES.keys())

        with col1:
            selected_state = st.selectbox(
                "State",
                options=[""] + available_states,
                index=0,
                key="state_select",
                help="Select a state to load zoning regulations"
            )

        # Load municipalities when state is selected
        municipalities_list = []
        if selected_state:
            # Check if we need to load municipalities
            if st.session_state.selected_state != selected_state:
                st.session_state.selected_state = selected_state
                st.session_state.municipalities_dict = None
                st.session_state.selected_municipality = None
                st.session_state.rag_chunks = None
                st.session_state.is_ready = False

            if st.session_state.municipalities_dict is None:
                with st.spinner("Loading municipalities..."):
                    st.session_state.municipalities_dict = fetch_municipalities(
                        selected_state, api_keys['firecrawl']
                    )

            if st.session_state.municipalities_dict:
                municipalities_list = sorted(st.session_state.municipalities_dict.keys())

        with col2:
            if selected_state:
                selected_municipality = st.selectbox(
                    "Municipality",
                    options=[""] + municipalities_list,
                    index=0,
                    key="municipality_select",
                    help="Select a municipality to search its zoning regulations"
                )
            else:
                st.selectbox(
                    "Municipality",
                    options=[""],
                    index=0,
                    disabled=True,
                    help="Please select a state first"
                )
                selected_municipality = ""

        # Detect municipality change and trigger processing
        if selected_municipality and selected_municipality != st.session_state.selected_municipality:
            st.session_state.selected_municipality = selected_municipality
            st.session_state.rag_chunks = None
            st.session_state.is_ready = False
            st.session_state.processing = True
            st.rerun()

        # Process if needed
        if st.session_state.processing and selected_state and selected_municipality:
            with st.status("Preparing data...", expanded=True) as status:
                success = prepare_municipality_data(
                    selected_state,
                    selected_municipality,
                    api_keys
                )
                st.session_state.processing = False
                if success:
                    status.update(label="Ready!", state="complete")
                else:
                    status.update(label="Failed", state="error")
            st.rerun()

    # Status indicator
    if st.session_state.status_message:
        if st.session_state.is_ready:
            st.success(st.session_state.status_message)
        elif "Failed" in st.session_state.status_message or "Could not" in st.session_state.status_message:
            st.error(st.session_state.status_message)
        else:
            st.info(st.session_state.status_message)

    st.markdown("---")

    # Question input - always visible, but disabled until ready
    is_ready = st.session_state.is_ready and st.session_state.rag_chunks is not None

    question = st.text_input(
        "Ask a question about zoning regulations:",
        placeholder="e.g., What are the setback requirements for residential zones?" if is_ready else "Select a state and municipality first...",
        disabled=not is_ready,
        key="question_input"
    )

    # Process question
    if question and is_ready:
        with st.spinner("Searching document..."):
            answer = search_rag(
                question,
                api_keys['openrouter'],
                state=st.session_state.selected_state,
                municipality=st.session_state.selected_municipality
            )

        if answer:
            st.markdown("### Answer")
            st.markdown(answer)


if __name__ == "__main__":
    main()
