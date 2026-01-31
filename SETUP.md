# Connecticut Zoning Regulations Finder

This Streamlit app helps you find zoning regulations for Connecticut towns using Firecrawl.

## Setup Instructions

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get API keys:**

   **Firecrawl API Key (Required):**
   - Visit [https://www.firecrawl.dev/app/](https://www.firecrawl.dev/app/)
   - Sign up and get your API key

   **OpenRouter API Key (Required):**
   - Visit [https://openrouter.ai/keys](https://openrouter.ai/keys)
   - Sign up and get your API key
   - This is used for AI-powered PDF selection using Claude

   **Reducto API Key (Optional - for RAG search):**
   - Visit [https://reducto.ai](https://reducto.ai)
   - Sign up and get your API key
   - This enables the RAG (Retrieval Augmented Generation) feature to search within PDF documents

3. **Set up your API keys (choose one method):**

   **Method 1: Using .env file (Recommended)**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and replace the placeholder values with your actual API keys:
     ```
     FIRECRAWL_API_KEY=fc-your-actual-api-key
     OPENROUTER_API_KEY=sk-or-your-actual-api-key
     REDUCTO_API_KEY=your-reducto-api-key  # Optional - for RAG search
     ```

   **Method 2: Enter in UI**
   - Just run the app and enter your API keys in the input fields when prompted

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```

5. **Use the app:**
   - Select a Connecticut town from the dropdown
   - Click "Search for Zoning Regulations"
   - The app will crawl the town's official website and display zoning regulation links

## How it works

- The app automatically fetches all Connecticut towns from public data sources
- Uses Firecrawl API to search for zoning regulations
- **AI-powered selection**: Uses Claude via OpenRouter to intelligently analyze and select the most relevant official zoning regulations PDF
- Displays the recommended PDF prominently, with all search results available in an expandable section
- **RAG Search** (optional): Process the selected PDF with Reducto to extract structured content, then ask natural language questions about the document
- You can download PDFs directly from the results

## Features

- **🤖 AI-Powered PDF Selection**: Uses Claude to intelligently identify the official zoning regulations document
- **🔍 RAG Document Search**: Process PDFs with Reducto and search within them using natural language questions
- Dynamic town list (no hardcoded values)
- Cached data for better performance
- PDF detection and smart filtering
- Clean, user-friendly interface
- Fallback to manual selection if AI recommendation is not suitable
