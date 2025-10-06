# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multi-agent AI chatbot system specialized in Korean customs and trade law, featuring hybrid RAG (AI + TF-IDF) search and structured legal document parsing.

## Development Commands

### Running the Application
```bash
streamlit run main.py
```

### Downloading Law Packages
```bash
python download_packages.py
```
This downloads law packages from the Korean law API and saves them to `./laws/` directory as JSON files.

### Environment Variables Required
- `GOOGLE_API_KEY` - For Gemini AI models
- `LAW_API_KEY` - For Korean law API (법령 API)
- `ADMIN_API_KEY` - For administrative rules API (행정규칙 API)

## Architecture

### Multi-Agent System

The chatbot uses a hierarchical multi-agent architecture:

1. **Query Analysis** (`analyze_query` in [utils.py](utils.py))
   - Extracts keywords using Gemini AI
   - Generates similar questions (3 variations)
   - Combines keywords for enhanced search

2. **Specialized Agents** (one per law package)
   - Each law package has its own agent (e.g., customs_investigation, foreign_exchange, etc.)
   - Agents run in parallel using `ThreadPoolExecutor`
   - Each agent searches its specific law data using TF-IDF

3. **Head Agent** (`get_head_agent_response_stream` in [utils.py](utils.py))
   - Synthesizes responses from all specialized agents
   - Provides streaming final answer
   - Handles conflicting information

### Data Pipeline

```
PDF/API → JSON (조번호, 제목, 내용) → TF-IDF Vectorization → Search Index
```

**Law Data Processing:**
- Law API: Regular laws (법률) via `lawapi.py`
- Admin API: Administrative rules (행정규칙) via `adminapi.py`
- Three-Stage Comparison: Hierarchical law comparison (법률-시행령-시행규칙) with automatic hierarchy extraction

### Hybrid RAG Search

The search system combines:
1. **AI-powered query expansion** (Gemini 2.5 Flash)
   - Extracts keywords and synonyms
   - Uses law-specific term dictionary extracted from all loaded law titles
   - Generates semantically similar questions

2. **TF-IDF vector search** (scikit-learn)
   - Dual vectorization: content + titles (separately weighted)
   - Custom legal stopwords filtering
   - Cosine similarity scoring
   - Configurable search weights (`search_weights` parameter)

3. **Search modes** (configurable via UI):
   - Content-only mode (`title: 0.0, content: 1.0`) - Default
   - Balanced mode (`title: 0.5, content: 0.5`) - For laws with detailed article titles

## Key Files

### Core Application
- [main.py](main.py) - Streamlit app entry point, package management, UI
- [utils.py](utils.py) - RAG search engine, embeddings, AI agents
- [law_article_search.py](law_article_search.py) - Text search with highlighting

### Law Data APIs
- [lawapi.py](lawapi.py) - Law API client, three-stage comparison parser
- [adminapi.py](adminapi.py) - Admin rules API client, smart article parser with hierarchy extraction

### Download & Processing
- [download_packages.py](download_packages.py) - Pre-downloads 5 law packages to `./laws/`

## Package System

### Available Packages
Located in `./laws/` directory:
- `customs_investigation.json` - 관세조사
- `foreign_exchange_investigation.json` - 외환조사
- `foreign_trade.json` - 대외무역
- `free_trade_agreement.json` - 자유무역협정
- `refund.json` - 환급

### Package Structure
```json
{
  "법령명": {
    "type": "law|admin|three_stage",
    "data": [
      {
        "조번호": "제1조",
        "제목": "목적",
        "내용": "이 법은..."
      }
    ]
  }
}
```

### Package Loading Flow
1. User selects package from UI buttons
2. `load_selected_packages()` checks cache first
3. If not cached, loads from JSON file
4. Auto-processes: JSON → TF-IDF embeddings
5. Stores in session state for chatbot use

## Administrative Rules Parser (adminapi.py)

### Smart Three-Stage Parsing System

The `SmartParser` class uses a sophisticated three-stage approach to parse administrative rules:

**Stage 1: Simple Article Parsing**
- Extracts articles with pattern `제X조(제목)`
- Filters out references using context analysis (checks 25 chars after pattern)
- Removes sentence-style titles (ending with 한다, 해야, etc.)

**Stage 2: Hierarchy Extraction**
- Identifies 장(chapter), 절(section), 관(subsection) boundaries
- Filters valid hierarchies by cross-referencing actual numbers in text
- Tracks hierarchy positions for accurate matching

**Stage 3: Article-Hierarchy Matching**
- Splits text by chapters for accurate scope
- Matches articles to their containing hierarchies
- Combines hierarchy titles: "장, 절, 관, 조문제목"

### Key Design Patterns

**Reference Detection** (`is_article_reference`, `is_hierarchy_reference`):
- Checks 25 characters after pattern for context clues
- Detects list words (및, 또는, 내지)
- Detects connective particles (의 규정, 에 따라)
- Prevents false positives from cross-references

**Number Prediction** (`NumberPredictor`):
- Handles complex Korean law numbering: 제1-5조의2
- Predicts next possible article numbers
- Used for validation and gap detection

## Session State Management

Critical session state variables:
- `chat_history` - Conversation history
- `law_data` - Processed law metadata
- `embedding_data` - TF-IDF vectors (vectorizer, title_vectorizer, matrix, title_matrix, chunks)
- `collected_laws` - Raw law JSON data
- `package_cache` - Previously loaded packages
- `search_weights` - Search mode configuration (`{'content': 1.0, 'title': 0.0}`)
- `event_loop` - Asyncio loop for async operations

## Caching Strategy

### Embedding Cache
- Location: `./cache/` directory
- Key: `{file_name}_{md5_hash}.pkl`
- Contents: `(vectorizers, matrices, chunks)` tuple
- Invalidation: Auto-detects old format (3-tuple vs 5-tuple)

### Package Cache
- In-memory session state cache
- Key: `"_".join(sorted(package_ids))`
- Enables instant switching between package combinations
- Previous selections saved before loading new ones

## Law Document Structure

### Standard Format (Law API & Admin API)
```
조번호: 제1조, 제1-5조, 제3조의2
제목: 목적 (from 괄호 inside article)
내용: Full article content including 항, 호, 목
```

### Three-Stage Comparison Format
```
조번호: 제1조 (from 법률)
제목: Combined hierarchy - "장, 절, 조문제목"
내용: 법률 + [시행령 X조] + [시행규칙 X조] + [위임행정규칙]
```

## Important Implementation Notes

### Search Weight Configuration
The `search_weights` parameter controls search strategy:
- `{'content': 1.0, 'title': 0.0}` - Ignores article titles, searches content only (default)
- `{'content': 0.5, 'title': 0.5}` - Balanced search for laws with meaningful titles
- This affects both keyword extraction and TF-IDF scoring

### TF-IDF Configuration
```python
TfidfVectorizer(
    ngram_range=(1, 2),  # Unigrams + bigrams
    stop_words=LEGAL_STOPWORDS,  # Custom legal stopwords
    sublinear_tf=True,  # Log scaling
    norm='l2'  # L2 normalization
)
```

### Error Handling in Multi-Agent System
- Individual agent failures don't crash the system
- Failed agents are reported in head agent synthesis
- Head agent proceeds with successful responses only

### Preprocessing Rules
- Remove `<...>` tags except `<삭 제>` (deleted marker)
- Extract titles from parentheses in article headers
- Filter chapter/section/subsection markers from article lists

## Testing Considerations

When testing law parsing:
1. Check for missing 목(mok) items - they're often skipped in APIs
2. Verify hierarchy matching across chapter boundaries
3. Test reference filtering with cross-references
4. Validate three-stage comparison merging

## UI Components

### Main Tabs
- **AI 챗봇 Tab** - Multi-agent Q&A with streaming responses
- **법령 검색 Tab** - Full-text search with highlighting

### Package Selection
- Radio-button style selection (single package at a time)
- Auto-loads and processes on selection
- Shows package info in sidebar

### Search Settings
Expandable panel with radio options:
- 내용 전용 모드 - Content-only search
- 균형 모드 - Balanced title+content search
