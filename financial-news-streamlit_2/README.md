# Financial News Intelligence - Streamlit Application

A modern, Python-based financial news intelligence platform powered by LangGraph's 7-agent AI pipeline. This application helps investors stay informed about important news and events related to their stock watchlist.

## Features

### 1. **Stock Watchlist Management**
- Add/remove stock tickers to monitor
- Real-time watchlist sync
- Support for any publicly traded stock

### 2. **AI-Powered News Digest Generation**
- 7-agent LangGraph pipeline:
  - **Agent 1**: Watchlist & Context (fetch company metadata)
  - **Agent 2**: News Retrieval (fetch articles from multiple sources)
  - **Agent 3**: Noise Filtering (remove duplicates and low-quality articles)
  - **Agent 4**: Event Clustering (group related articles)
  - **Agent 5**: Impact Summarization (generate TLDR and impact analysis)
  - **Agent 6**: Importance Ranking (score events 0-100)
  - **Agent 7**: Email Packaging (format digest)

### 3. **Event Display & Analysis**
- Event cards with importance badges (High/Medium/Low)
- Detailed event information:
  - TLDR summaries
  - Key bullet points
  - Impact analysis
  - Verification status
  - Source count and links
- Filtering by importance level

### 4. **Digest History & Archive**
- View all previously generated digests
- Filter and search digests
- Export digests as HTML or plain text
- Delete old digests

### 5. **LLM Provider Configuration**
- Support for OpenAI (GPT-4, GPT-3.5 Turbo)
- Support for Google Gemini
- Easy API key management
- Provider switching

### 6. **Export Functionality**
- Download digests as HTML (for email)
- Download digests as plain text
- Preserve formatting and styling

## Installation

### Prerequisites
- Python 3.11+
- pip or conda
- OpenAI API key OR Google Gemini API key

### Setup

1. **Clone or download the project:**
```bash
cd financial-news-streamlit
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables (optional):**
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Running the Application

### Development Mode
```bash
streamlit run app.py
```

The application will open at `http://localhost:8501`

### Production Deployment
```bash
streamlit run app.py --logger.level=error --client.showErrorDetails=false
```

## Usage Guide

### 1. **Add Stock Tickers**
- Navigate to "Watchlist" tab
- Enter stock ticker symbols (e.g., AAPL, NVDA, TSLA)
- Click "Add" to add to watchlist
- Remove tickers using the "Remove" button

### 2. **Generate Digest**
- Go to "Dashboard" tab
- Click "⚡ Generate Digest" button
- Wait for pipeline execution (~4-5 seconds)
- View generated events sorted by importance

### 3. **View Event Details**
- Click on any event card to expand
- Read TLDR, key points, and impact analysis
- Check verification status and source count

### 4. **Export Digest**
- After generating a digest, click "Download as HTML" or "Download as Text"
- Save to your computer
- Share or archive as needed

### 5. **Configure LLM Provider**
- Go to "Settings" tab
- Select OpenAI or Google Gemini
- Enter your API key
- Click "Save Configuration"

## Architecture

### Frontend
- **Streamlit**: Python-based UI framework
- **Pandas**: Data manipulation and display
- **Plotly**: Data visualization

### Backend
- **LangGraph**: Agent orchestration framework
- **LangChain**: LLM integration
- **yfinance**: Stock data retrieval
- **feedparser**: RSS feed parsing

### Data Storage
- **JSON Files**: Simple file-based storage (no database required)
  - `data/watchlist.json` - User watchlists
  - `data/digests.json` - Generated digests and events
  - `data/settings.json` - User settings and LLM configuration

### LLM Integration
- **OpenAI API**: GPT-4 and GPT-3.5 Turbo
- **Google Gemini API**: Gemini Pro and Vision models

## Project Structure

```
financial-news-streamlit/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── data/                     # JSON data files (auto-created)
│   ├── watchlist.json        # User watchlists
│   ├── digests.json          # Generated digests
│   └── settings.json         # User settings
├── utils/
│   ├── __init__.py
│   ├── session.py            # Session state management
│   ├── database.py           # JSON file operations
│   └── pipeline.py           # Pipeline integration
└── pages/
    ├── __init__.py
    ├── watchlist.py          # Watchlist management UI
    ├── digest.py             # Digest generation UI
    ├── history.py            # Digest history UI
    └── settings.py           # Settings UI
```

## Configuration

### Environment Variables

Create a `.env` file in the project root (optional):

```env
# LLM Configuration
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# Application
DEBUG=False
LOG_LEVEL=INFO
```

Note: All data is stored in JSON files in the `data/` directory. No database setup required!

### API Keys

**OpenAI:**
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy and paste into Settings

**Google Gemini:**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy and paste into Settings

## Performance

- **Pipeline Execution**: ~4-5 seconds
- **Event Generation**: 3-10 events per digest
- **Database Queries**: <100ms average
- **UI Response Time**: <1 second

## Limitations

- Maximum 50 tickers per watchlist (configurable)
- News retrieval limited by API rate limits
- LLM API costs apply (OpenAI/Gemini)
- JSON storage suitable for single-user; consider database for multi-user

## Troubleshooting

### "No tickers in watchlist"
- Add tickers in the Watchlist tab first
- Supported formats: AAPL, NVDA, TSLA, etc.

### "Pipeline failed"
- Check LLM API key in Settings
- Verify internet connection
- Check API rate limits

### "Data not persisting"
- Check that `data/` directory exists and is writable
- Ensure JSON files are not corrupted
- Delete `data/` directory and restart to reset (will lose data)

### "Import errors"
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.11+)

## Future Enhancements

1. **Multi-user Support**: Add authentication and user accounts
2. **Email Delivery**: Schedule and email digests automatically
3. **Real-time Updates**: WebSocket integration for live news
4. **Advanced Filtering**: Filter by event type, sector, etc.
5. **Backtesting**: Analyze historical digest accuracy
6. **Mobile App**: React Native or Flutter version
7. **API Integration**: REST API for external tools
8. **Analytics Dashboard**: Track digest usage and trends

## Contributing

To contribute improvements:
1. Create a new branch
2. Make changes
3. Test thoroughly
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or feature requests, please open an issue on GitHub or contact support.

## Acknowledgments

- LangGraph for agent orchestration
- Streamlit for the UI framework
- OpenAI and Google for LLM APIs
- yfinance for stock data

---

**Version**: 1.0  
**Last Updated**: March 2026  
**Maintainer**: Financial News Intelligence Team
