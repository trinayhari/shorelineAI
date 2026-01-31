"""
Module for AI-powered selection of zoning regulation PDFs using OpenRouter
"""
import streamlit as st
from openai import OpenAI
import json
from config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS


def select_best_pdf_with_llm(municipality_name, state_name, results, openrouter_api_key):
    """
    Use OpenRouter LLM to intelligently select the best zoning regulations PDF
    from the search results.

    Args:
        municipality_name: Name of the municipality (town/city)
        state_name: Name of the state
        results: List of result dictionaries with 'url', 'title', 'is_pdf', etc.
        openrouter_api_key: API key for OpenRouter

    Returns:
        The selected result dictionary, or None if no good match found
    """
    try:
        if not results or len(results) == 0:
            return None

        # Filter to only PDFs for analysis
        pdf_results = [r for r in results if r.get('is_pdf', False)]

        if len(pdf_results) == 0:
            st.warning("No PDF files found")
            return None

        if len(pdf_results) == 1:
            return pdf_results[0]

        # Prepare the results for LLM analysis
        results_text = ""
        for idx, result in enumerate(pdf_results[:10], 1):  # Limit to top 10 PDFs
            results_text += f"{idx}. URL: {result.get('url', 'N/A')}\n"

            # Include link text if available (this is the actual text shown on the webpage)
            link_text = result.get('link_text')
            if link_text:
                results_text += f"   Link Text: {link_text}\n"

            results_text += f"   Filename: {result.get('title', 'N/A')}\n"
            results_text += f"   Relevance Score: {result.get('relevance', 0)}\n\n"

        # Initialize OpenAI client with OpenRouter
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )

        # Create the prompt for the LLM
        prompt = f"""You are analyzing search results to find the official zoning regulations PDF for {municipality_name}, {state_name}.

Search Results (PDFs only):
{results_text}

Your task: Identify which PDF is most likely to be the OFFICIAL, COMPLETE zoning regulations document for {municipality_name}.

Look for:
- **Link Text is the most reliable indicator** - if the link text says "Zoning Regulations" or "Zoning Ordinance", that's a strong signal
- Official town/city/municipality zoning regulations or ordinances
- Complete regulation documents (not amendments, applications, or forms)
- Most recent/current versions (2024-2025 preferred)
- **AVOID these types of documents:**
  - Summaries or synopses of regulations
  - Proposed changes or amendments
  - Draft regulations (not yet adopted)
  - Applications or forms
  - Meeting minutes or agendas
  - Individual amendments (look for the complete document instead)

Respond with ONLY a JSON object in this exact format:
{{
  "selected_index": <number 1-{len(pdf_results[:10])} or null if none are suitable>,
  "confidence": "<high|medium|low>",
  "reasoning": "<brief explanation of why this PDF was selected or why none are suitable>"
}}"""

        # Call the LLM
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS
        )

        # Parse the response
        llm_response = response.choices[0].message.content.strip()

        # Extract JSON from response (handle potential markdown code blocks)
        if "```json" in llm_response:
            llm_response = llm_response.split("```json")[1].split("```")[0].strip()
        elif "```" in llm_response:
            llm_response = llm_response.split("```")[1].split("```")[0].strip()

        result_json = json.loads(llm_response)

        selected_index = result_json.get("selected_index")
        confidence = result_json.get("confidence", "unknown")
        reasoning = result_json.get("reasoning", "No reasoning provided")

        # Return selected result
        if selected_index is not None and 1 <= selected_index <= len(pdf_results[:10]):
            selected_result = pdf_results[selected_index - 1]
            return selected_result
        else:
            st.warning("No suitable zoning regulations found")
            return None

    except Exception as e:
        st.error(f"AI selection error: {str(e)}")
        # Fallback to highest relevance score
        pdf_results = [r for r in results if r.get('is_pdf', False)]
        if pdf_results:
            st.info("Using highest relevance score instead")
            return pdf_results[0]
        return None
