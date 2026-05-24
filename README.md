# 🤖 RepoMiner - RAG GitHub Repository Chatbot

An intelligent code analysis chatbot that uses **Retrieval-Augmented Generation (RAG)** to answer questions about any GitHub repository. Built with Python, Streamlit, LangChain, ChromaDB, and Google Gemini AI.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/LangChain-0.1+-green.svg)](https://langchain.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Latest-orange.svg)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Table of Contents


---

## 🎯 Features

### Core Capabilities
- **🔄 Dynamic Repository Ingestion**: Clone and analyze any public GitHub repository on-demand
- **🧠 Syntax-Aware Code Chunking**: Uses LangChain's `LanguageParser` with tree-sitter to respect code structure (functions, classes)
- **💬 Conversational Memory**: Maintains chat context for follow-up questions
- **🕘 Persistent Repo Sessions**: Saves chat history, stats, and vector snapshots locally so you can return to earlier repositories later
- **⚡ Fast AI Inference**: Powered by Google Gemini 1.5 Flash with 1M token context
- **📊 Repository Analytics**: Displays tech stack, file counts, and processing stats
- **📈 Advanced Analytics**: Contributor activity, dependency scan, file hotspots, and security signal checks
- **⬇️ Exportable Reports**: Download repository summaries as CSV or JSON
- **🎨 Modern UI**: Clean Streamlit interface with real-time status updates

### Supported File Types
- **Documentation**: `.md`, `.txt`
- **Images**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`

### Session Management
- Each analyzed repo is stored locally in `.repominer_state/`
- The app restores the last active repository automatically on launch
- Use the chatbot sidebar to switch between previously analyzed repositories

---

## 🚀 Quick Start

- **Python 3.9+** installed
- **Git** installed  
- **Google Gemini API Key** (free - https://aistudio.google.com/apikey)
- (Optional) **OpenRouter API Key** for fallback support
- (Optional) **Groq API Key** for additional LLM options

### Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/repominer.git
cd repominer
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

**Expected time:** 3-5 minutes

#### 3. Configure API Keys

Create a `.env` file in the root directory and add your API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

**Get your free keys:**
1. Visit https://aistudio.google.com/apikey and create a Gemini key
2. (Optional) Create an OpenRouter account for fallback support
3. (Optional) Create a Groq account for additional model options

#### 4. Run the Application
```bash
streamlit run app.py
```

The app will automatically open at `http://localhost:8501`

---

## 🧠 How It Works

### RAG Pipeline Architecture

```
User Question
     ↓
┌─────────────────────────────┐
│   Question Embedding        │  Convert text to vector
└────────────┬────────────────┘
             ↓
┌─────────────────────────────┐
│   Vector Search (ChromaDB)  │  Find relevant code chunks
└────────────┬────────────────┘
             ↓
┌─────────────────────────────┐
│   Context Assembly          │  Combine relevant code
└────────────┬────────────────┘
             ↓
┌─────────────────────────────┐
│   LLM Generation (Gemini)   │  Generate answer with context
└────────────┬────────────────┘
             ↓
          Answer
```

### Step-by-Step Process

#### 1. **Repository Ingestion**
```
GitHub Repository
     ↓
Clone Repository
     ↓
Parse Code Files (syntax-aware)
     ↓
Generate Embeddings (384-dimensional vectors)
     ↓
Store in ChromaDB Vector Database
```

#### 2. **Question Processing**
```
User Question
     ↓
Convert to Embedding
     ↓
Search ChromaDB (retrieve top 6 relevant chunks)
     ↓
Create Prompt with Context + Question
     ↓
Send to Gemini AI
     ↓
Return Answer with Code References
```

---

## 📁 Project Structure

```
repominer/
│
├── app.py                          # Main Streamlit application entry point
├── config.py                       # Configuration and environment setup
├── ui.py                           # UI components and styling
├── ingest.py                       # Repository ingestion and processing
├── repo_session_store.py           # Session management and persistence
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── LICENSE                         # MIT License
│
├── pages/                          # Streamlit multi-page app
│   ├── 1_📊_Repository_Stats.py   # Repository analytics and statistics
│   ├── 2_📚_How_to_Use.py         # User guide and instructions
│   └── 3_💬_Chatbot.py            # Main RAG chatbot interface
│
├── .env                            # Environment variables (not committed)
├── .gitignore                      # Git ignore rules
│
├── .streamlit/                     # Streamlit configuration (auto-generated)
├── .repominer_state/               # Session storage (auto-generated)
└── __pycache__/                    # Python cache (auto-generated)
```

### Key Files Explained

| File | Purpose |
|------|---------|
| `app.py` | Landing page and main navigation |
| `config.py` | API key and configuration management |
| `ui.py` | Reusable UI components |
| `ingest.py` | GitHub cloning, parsing, embedding, and ChromaDB storage |
| `repo_session_store.py` | Session persistence and loading |
| `pages/3_💬_Chatbot.py` | RAG pipeline with LangChain and Gemini |
| `pages/1_📊_Repository_Stats.py` | Analytics and visualization |
| `pages/2_📚_How_to_Use.py` | User guide |

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **UI Framework** | Streamlit 1.30+ | Modern web interface |
| **RAG Orchestration** | LangChain 0.1+ | Chains, retrievers, document processing |
| **Vector Database** | ChromaDB | HNSW-based similarity search |
| **Embeddings** | HuggingFace all-MiniLM-L6-v2 | 384-dim sentence embeddings |
| **LLM** | Google Gemini 1.5 Flash | Fast inference with 1M token context |
| **Code Parsing** | LangChain LanguageParser + tree-sitter | Syntax-aware code chunking |
| **Git Operations** | GitPython | Repository cloning |
| **Environment** | Python-dotenv | Environment variable management |

---

## 📚 Usage Guide

### First-Time Setup

1. **Start the application:**
   ```bash
   streamlit run app.py
   ```

2. **Navigate to the Chatbot page** (from sidebar)

3. **Process a repository:**
   - Enter GitHub URL: `https://github.com/username/repository`
   - Click "🚀 Process Repository"
   - Wait 1-5 minutes (depends on repo size)

4. **Start asking questions!**

### Example Questions
- "What is the overall architecture of this project?"
- "How does authentication work?"
- "Explain the API endpoints"
- "What database is being used?"
- "Show me the component structure"
- "What styling framework is used?"

### Best Practices

#### ✅ Good Questions
- Be specific: "How does user login validation work?"
- Reference components: "Explain the AuthContext component"
- Ask follow-ups: The bot remembers conversation context
- Check sources: File paths are mentioned in responses

#### ❌ Avoid
- Questions about code execution (the bot reads, doesn't run)
- Questions requiring external documentation
- Questions about deployment (unless in code comments)

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with your API keys:

```env
# Primary LLM
GEMINI_API_KEY=your_gemini_key_here

# Fallback LLMs (optional)
OPENROUTER_API_KEY=your_openrouter_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### Embedding Model

The application uses `all-MiniLM-L6-v2` for embeddings:
- **Dimension**: 384
- **Speed**: Fast (CPU-compatible)
- **Model Size**: 22MB
- **License**: Apache 2.0

### Chunking Parameters

```python
CHUNK_SIZE = 1000      # Characters per chunk (~250 tokens)
CHUNK_OVERLAP = 200    # Overlap to prevent mid-function splits
```

### Retrieval Configuration

```python
search_type = "similarity"  # Cosine similarity search
top_k = 6                   # Retrieve top 6 relevant chunks
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. **API Key Error**
**Solution:**
- Get key from https://aistudio.google.com/apikey
- Add to `.env` file: `GEMINI_API_KEY=your_key`
- Restart Streamlit: `streamlit run app.py`

#### 2. **Repository Not Found**
**Cause:** GitHub URL is incorrect or private  
**Solution:** Ensure URL is public and formatted as `https://github.com/user/repo`

#### 3. **Empty Responses / No Context Retrieved**
**Cause:** Repository not processed correctly  
**Solution:**
- Click "🚀 Process Repository" again
- Check console for error messages
- Ensure repository has code files

#### 4. **Rate Limit Exceeded**
**Cause:** API quota exceeded  
**Solution:** 
- Add OpenRouter and Groq keys for fallback options
- Wait a few minutes before retrying

#### 5. **ModuleNotFoundError**
**Solution:**
```bash
pip install -r requirements.txt
```

#### 6. **ChromaDB Permission Error (Windows)**
**Solution:** Already handled - vectors are stored with proper permissions

---

## 🌟 Advanced Features

### Conversational Memory

The chatbot remembers conversation history:
```
You: "What frontend framework is used?"
Bot: "The project uses React with React Router..."

You: "What state management does it use?"
Bot: "It uses React Context API, as mentioned before..."
       ↑ Remembers previous context
```

### Syntax-Aware Chunking

Uses tree-sitter to parse code intelligently:
- Respects function boundaries
- Keeps classes together
- Maintains logical code blocks

### Session Persistence

- Sessions are automatically saved
- Switch between repositories using the sidebar
- Chat history is preserved
- Repository statistics are cached

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/repominer.git
cd repominer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### Code Style

- Follow PEP 8 guidelines
- Add docstrings to functions
- Test changes with sample repositories

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Support

For issues, questions, or suggestions:
1. Check the [Troubleshooting](#-troubleshooting) section
2. Review the [Usage Guide](#-usage-guide)
3. Open an issue on GitHub

---

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [LangChain](https://langchain.com/)
- Embeddings from [HuggingFace](https://huggingface.co/)
- Vector storage by [ChromaDB](https://www.trychroma.com/)
- LLM: [Google Gemini AI](https://gemini.google.com/)

---

**Happy analyzing! 🚀**
