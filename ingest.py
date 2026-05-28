"""
ADVANCED MULTIMODAL REPOSITORY INGESTION MODULE
=================================================

This module handles the complete ingestion pipeline for GitHub repositories:
1. Clones repository using GitPython
2. Detects programming languages and file types
3. Uses LangChain's LanguageParser for syntax-aware code chunking
4. Processes images with vision AI (placeholder for future integration)
5. Generates embeddings using HuggingFace all-MiniLM-L6-v2
6. Stores everything in ChromaDB with metadata

KEY TECHNICAL DECISIONS:
- LanguageParser: Respects code structure (functions, classes) rather than naive splitting
- RecursiveCharacterTextSplitter: Fallback for non-code files (MD, TXT)
- ChromaDB: Uses HNSW indexing for fast approximate nearest-neighbor search
- Metadata tracking: Stores file paths, languages, chunk IDs for traceability

Author: CodeMiner
Date: March 2026
"""

import json
import os
import shutil
import stat
from pathlib import Path
from typing import Tuple, Dict, List
from collections import Counter

from git import Repo
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from advanced_analytics import (
    compute_language_insights,
    summarize_language_insights,
)
from architecture_reports import generate_architecture_mermaid

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# CLONE DIRECTORY: Temporary storage for cloned repos
# Using a consistent path allows ChromaDB to reference source files correctly
CLONE_DIR = "./cloned_repo"

# CHROMA PERSIST DIRECTORY: Where vector embeddings are stored
# ChromaDB uses SQLite for metadata + hnswlib for vector indices
CHROMA_DIR = "./chroma_db"

# SUPPORTED FILE EXTENSIONS
# These extensions are processed with syntax-aware chunking
CODE_EXTENSIONS = {
    ".js": Language.JS,
    ".jsx": Language.JS,
    ".ts": Language.TS,
    ".tsx": Language.TS,
    ".py": Language.PYTHON,
    ".css": "CSS",
    ".html": Language.HTML,
    ".htm": Language.HTML,
    ".md": None,  # Markdown uses fallback splitter
    ".txt": None,
}

# Add common C/C++ extensions so the GenericLoader will include them
# Values map to a human-readable marker (parser auto-detection is used),
# using simple strings/None to avoid depending on Language.CPP availability.
CODE_EXTENSIONS.update({
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hh": "C++",
    ".hxx": "C++",
})

# Image extensions for multimodal processing
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg"}

# CHUNKING PARAMETERS
# These values balance context preservation with token limits
CHUNK_SIZE = 1000  # Characters per chunk (approx 250 tokens)
CHUNK_OVERLAP = 200  # Overlap prevents splitting mid-function


# ==============================================================================
# WINDOWS-COMPATIBLE DIRECTORY REMOVAL
# ==============================================================================


def remove_readonly(func, path, excinfo):
    """
    Error handler for shutil.rmtree that fixes Windows permission issues.

    WINDOWS GIT ISSUE:
    Git on Windows marks files in .git/objects as read-only to prevent corruption.
    When Python tries to delete these files, it raises PermissionError.

    SOLUTION:
    1. Remove the read-only attribute using os.chmod
    2. Retry the deletion operation

    This is the recommended approach from Python docs and Git-for-Windows community.

    Args:
        func: The function that raised the exception (os.unlink or os.rmdir)
        path: Path to the file/directory that couldn't be deleted
        excinfo: Exception information tuple
    """
    # Clear the read-only bit (stat.S_IWRITE gives write permission)
    os.chmod(path, stat.S_IWRITE)
    # Retry the deletion
    func(path)


def safe_rmtree(path):
    """
    Cross-platform directory removal that handles Windows read-only files.

    Uses the remove_readonly error handler to fix permission issues on-the-fly.
    On Linux/Mac, behaves identically to shutil.rmtree.

    Args:
        path: Directory path to remove
    """
    if os.path.exists(path):
        shutil.rmtree(path, onerror=remove_readonly)


# ==============================================================================
# MULTIMODAL PROCESSING: IMAGE ANALYSIS
# ==============================================================================


def process_image_with_vision(image_path: str) -> str:
    """
    PLACEHOLDER: Extracts text/diagrams from images using vision AI.

    In a production system, this would:
    1. Use OpenAI GPT-4V or Google Gemini Vision to analyze diagrams
    2. Extract text from flowcharts, architecture diagrams, screenshots
    3. Generate semantic descriptions of UI mockups
    4. OCR code snippets from images

    INTEGRATION EXAMPLE (future):
    ```python
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    with open(image_path, "rb") as img:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this code diagram in detail."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]
            }]
        )
    return response.choices[0].message.content
    ```

    WHY VISION AI FOR CODE REPOS?
    - Architecture diagrams in docs/ folders contain critical system design info
    - Flowcharts explain complex logic better than code comments
    - UI screenshots show expected behavior
    - Making these searchable via embeddings massively improves RAG quality

    Args:
        image_path (str): Path to image file

    Returns:
        str: Extracted text description (currently simulated)
    """
    filename = Path(image_path).name

    # Simulate vision AI output
    # In production, replace with actual GPT-4V/Gemini API call
    simulated_description = f"""
    [IMAGE ANALYSIS - {filename}]
    This image appears to be part of the repository's documentation.
    Potential content types: architecture diagram, flowchart, UI mockup, or screenshot.
    
    For full multimodal support, integrate OpenAI GPT-4 Vision or Google Gemini.
    This placeholder ensures image metadata is indexed for future enhancement.
    """

    return simulated_description.strip()


# ==============================================================================
# REPOSITORY STATISTICS ANALYSIS
# ==============================================================================


def get_repo_stats(documents: List[Document], images_processed: int) -> Dict:
    """
    Analyzes processed repository to extract meaningful statistics.

    This provides users with immediate feedback about what was ingested,
    helping them understand the scope and tech stack of the repository.

    Args:
        documents: List of LangChain Document objects
        images_processed: Number of images analyzed

    Returns:
        dict: Repository statistics including file counts and tech stack
    """

    # Count by unique file path so the breakdowns report files, not chunks.
    # A single README chunked into many pieces should still count as one .md.
    unique_sources = {
        doc.metadata.get("source") for doc in documents if doc.metadata.get("source")
    }
    file_extensions = []
    chunk_extensions = []
    for source in unique_sources:
        ext = Path(source).suffix
        if ext:
            file_extensions.append(ext)
    for doc in documents:
        source = doc.metadata.get("source", "")
        if source:
            ext = Path(source).suffix
            if ext:
                chunk_extensions.append(ext)

    file_ext_counter = Counter(file_extensions)
    chunk_ext_counter = Counter(chunk_extensions)

    tech_map = {
        ".js": "JavaScript",
        ".jsx": "React",
        ".ts": "TypeScript",
        ".tsx": "React+TS",
        ".py": "Python",
        ".css": "CSS",
        ".html": "HTML",
        ".htm": "HTML",
        ".md": "Markdown",
    }

    # Language counts are by unique file so the donut reflects repo composition,
    # not how aggressive the chunker was on any one file.
    language_counts: Dict[str, int] = {}
    for ext, count in file_ext_counter.items():
        human = tech_map.get(ext, ext.lstrip(".") or "Other")
        language_counts[human] = language_counts.get(human, 0) + count

    extension_breakdown = {k: v for k, v in file_ext_counter.most_common()}
    chunk_breakdown = {k: v for k, v in chunk_ext_counter.most_common()}

    return {
        "total_files": len(unique_sources),
        "total_chunks": len(documents),
        "languages": language_counts,
        "images_processed": images_processed,
        "extension_breakdown": extension_breakdown,
        "chunk_breakdown": chunk_breakdown,
    }


# ==============================================================================
# REPOSITORY ANALYTICS HELPERS
# ==============================================================================


def _compute_contributors(repo_dir: str, limit: int = 10) -> List[Dict]:
    """Aggregate commits per author from the cloned repo's full git history."""
    try:
        repo = Repo(repo_dir)
    except Exception:
        return []

    counts: Counter = Counter()
    for commit in repo.iter_commits():
        name = (commit.author.name or "").strip() or "Unknown"
        counts[name] += 1

    return [
        {"name": name, "commits": count}
        for name, count in counts.most_common(limit)
    ]


def _compute_dependencies(repo_dir: str) -> List[Dict]:
    """Read declared dependencies from common manifest files.

    Currently supports `package.json` (Node) and `requirements.txt` (Python).
    Returns a list of {name, version, source} entries. License and vulnerability
    fields are intentionally left blank — populating them accurately requires a
    network call to npm/PyPI that we do not want to add here.
    """
    root = Path(repo_dir)
    deps: List[Dict] = []
    seen: set = set()

    def _add(name: str, version: str, source: str) -> None:
        key = (name, source)
        if not name or key in seen:
            return
        seen.add(key)
        deps.append({"name": name, "version": version or "", "source": source})

    # package.json — repo root only; nested node_modules manifests are noise.
    pkg_json = root / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            for field in ("dependencies", "devDependencies", "peerDependencies"):
                for name, version in (data.get(field) or {}).items():
                    _add(name, str(version), "package.json")
        except Exception:
            pass

    # requirements.txt and common pinned variants. Parse lazily: skip blanks,
    # comments, and editable/url installs that have no clean name@version form.
    for req_path in (
        root / "requirements.txt",
        root / "requirements" / "base.txt",
        root / "requirements" / "prod.txt",
    ):
        if not req_path.is_file():
            continue
        try:
            for raw_line in req_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Strip inline comments and environment markers.
                line = line.split("#", 1)[0].strip()
                line = line.split(";", 1)[0].strip()
                if not line:
                    continue
                name, _, version = line.partition("==")
                if not version:
                    name, _, version = line.partition(">=")
                if not version:
                    name, _, version = line.partition("~=")
                _add(name.strip(), version.strip(), req_path.name)
        except Exception:
            continue

    return deps[:60]


# ==============================================================================
# MAIN INGESTION PIPELINE
# ==============================================================================


def process_repository(github_url: str, persist_dir: str | None = None) -> Tuple[bool, Dict]:
    """
    Complete end-to-end repository ingestion pipeline.

    PIPELINE STAGES:
    1. Clone: Downloads repo using GitPython
    2. Load: Discovers files matching supported extensions
    3. Parse: Uses LanguageParser for syntax-aware chunking
    4. Multimodal: Processes images with vision AI
    5. Embed: Generates 384-dim vectors using all-MiniLM-L6-v2
    6. Store: Persists to ChromaDB with HNSW indexing

    LANGCHAIN LANGUAGEPARSER EXPLAINED:
    Traditional text splitting breaks code mid-function:
        def calculate_tax(income):
            if income < 10000:  # ❌ Chunk 1 ends here
                return 0        # ❌ Chunk 2 starts here

    LanguageParser respects AST (Abstract Syntax Tree):
        Chunk 1: [entire calculate_tax function]
        Chunk 2: [next complete function]

    This is CRITICAL because:
    - Retrieval finds complete, runnable code blocks
    - LLM sees full context (parameters, logic, return values)
    - Prevents confusing partial snippets

    CHROMADB STORAGE EXPLAINED:
    ChromaDB creates two data structures:
    1. SQLite DB (chroma.sqlite3): Stores metadata and document text
    2. HNSW Index (in UUID folders): Stores 384-dim embeddings

    When user asks a question:
    1. Question → all-MiniLM-L6-v2 → 384-dim query vector
    2. HNSW index finds k nearest vectors in O(log n) time
    3. Return associated code chunks from SQLite

    Args:
        github_url (str): Full GitHub repository URL

    Returns:
        tuple: (success: bool, stats: dict)
    """

    try:
        # ======================================================================
        # STAGE 1: CLONE REPOSITORY
        # ======================================================================

        # Clear previous clone to prevent conflicts
        if os.path.exists(CLONE_DIR):
            safe_rmtree(CLONE_DIR)

        # GitPython clone_from:
        # - Handles authentication for public repos automatically
        # - By default we clone full history for accurate analytics (contributors)
        # - For very large repos you can add depth=1 to speed up ingestion (less analytics)
        print(f"📥 Cloning repository: {github_url}")
        Repo.clone_from(github_url, to_path=CLONE_DIR)
        print(f"✅ Clone complete")

        # ======================================================================
        # STAGE 2: LOAD CODE FILES WITH SYNTAX-AWARE PARSING
        # ======================================================================

        print("🔍 Loading and parsing code files...")

        # GenericLoader.from_filesystem:
        # - glob="**/*": Recursively search all subdirectories
        # - suffixes: Only load files with these extensions
        # - exclude: Skip node_modules, build outputs, .git (reduces noise)
        # - parser: LanguageParser uses tree-sitter for AST parsing

        code_loader = GenericLoader.from_filesystem(
            CLONE_DIR,
            glob="**/*",
            suffixes=list(CODE_EXTENSIONS.keys()),
            exclude=[
                "**/node_modules/**",
                "**/dist/**",
                "**/build/**",
                "**/.git/**",
                "**/venv/**",
                "**/__pycache__/**",
            ],
            # LanguageParser Configuration:
            # - Uses tree-sitter grammars to parse code into AST
            # - parser_threshold=500: Minimum chars per chunk (prevents tiny snippets)
            # - Splits at function/class boundaries when possible
            parser=LanguageParser(
                language=Language.PYTHON,  # Default; auto-detected per file
                parser_threshold=500,
            ),
        )

        documents = code_loader.load()
        print(f"📄 Loaded {len(documents)} code chunks")

        # ======================================================================
        # STAGE 3: PROCESS MARKDOWN & TEXT FILES
        # ======================================================================

        # For non-code files (README.md, docs), use RecursiveCharacterTextSplitter
        # This splits on paragraph boundaries (\n\n) first, then sentences, then chars
        # Preserves semantic coherence better than fixed-size splitting

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],  # Priority order
        )

        # Find all .md and .txt files
        md_files = list(Path(CLONE_DIR).rglob("*.md"))
        txt_files = list(Path(CLONE_DIR).rglob("*.txt"))

        for file_path in md_files + txt_files:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if content.strip():  # Skip empty files
                        chunks = text_splitter.split_text(content)
                        for i, chunk in enumerate(chunks):
                            documents.append(
                                Document(
                                    page_content=chunk,
                                    metadata={
                                        "source": str(file_path.relative_to(CLONE_DIR)),
                                        "chunk_id": i,
                                        "type": "documentation",
                                    },
                                )
                            )
            except Exception as e:
                print(f"⚠️ Skipping {file_path}: {e}")

        print(f"📝 Total chunks after markdown: {len(documents)}")

        # ======================================================================
        # STAGE 4: MULTIMODAL - Process Images (DISABLED)
        # ======================================================================
        # Disabled because placeholder image descriptions pollute retrieval results.
        # Re-enable when actual vision AI (GPT-4V/Gemini) is integrated.

        # print("🖼️ Scanning for images...")
        images_processed = 0

        # Count images without processing them
        for img_ext in IMAGE_EXTENSIONS:
            for img_path in Path(CLONE_DIR).rglob(f"*{img_ext}"):
                images_processed += 1

        # for img_ext in IMAGE_EXTENSIONS:
        #     for img_path in Path(CLONE_DIR).rglob(f"*{img_ext}"):
        #         try:
        #             # Extract text description using vision AI (currently placeholder)
        #             description = process_image_with_vision(str(img_path))
        #
        #             # Store image description as a searchable document
        #             # This allows queries like "show me the architecture diagram"
        #             # to retrieve relevant images based on their content
        #             documents.append(
        #                 Document(
        #                     page_content=description,
        #                     metadata={
        #                         "source": str(img_path.relative_to(CLONE_DIR)),
        #                         "type": "image",
        #                         "format": img_ext,
        #                     },
        #                 )
        #             )
        #             images_processed += 1
        #         except Exception as e:
        #             print(f"⚠️ Error processing image {img_path}: {e}")

        print(f"🖼️ Found {images_processed} images (not indexed)")

        # ======================================================================
        # STAGE 5: GENERATE EMBEDDINGS & STORE IN CHROMADB
        # ======================================================================

        print("🧠 Generating embeddings with all-MiniLM-L6-v2...")

        # HuggingFace Embeddings Model
        # all-MiniLM-L6-v2 architecture:
        # - 6-layer transformer (vs 12 for BERT-base)
        # - 384-dimensional output (vs 768 for BERT)
        # - Trained with contrastive learning on sentence pairs
        # - Normalizes embeddings for cosine similarity
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # ChromaDB Vector Store Creation
        # from_documents:
        # 1. Calls embeddings.embed_documents() for each chunk
        # 2. Creates HNSW index for fast similarity search
        # 3. Stores metadata in SQLite for retrieval
        # 4. Persists to disk at CHROMA_DIR

        target_dir = persist_dir or CHROMA_DIR
        # Make sure the target dir is empty so we never append into a previous
        # repo's vectorstore (which is what produced the chunk-bleed bug).
        if os.path.exists(target_dir):
            safe_rmtree(target_dir)
        print(f"💾 Storing {len(documents)} chunks in ChromaDB at {target_dir}...")
        vectorstore = Chroma.from_documents(
            documents=documents, embedding=embeddings, persist_directory=target_dir
        )

        print("✅ Ingestion complete!")

        # ======================================================================
        # STAGE 6: GENERATE STATISTICS
        # ======================================================================

        stats = get_repo_stats(documents, images_processed)

        # Compute top largest files in the cloned repo for stats
        top_files = []
        try:
            all_files = [p for p in Path(CLONE_DIR).rglob("*") if p.is_file()]
            sizes = [
                (str(p.relative_to(CLONE_DIR)), p.stat().st_size) for p in all_files
            ]
            sizes.sort(key=lambda x: x[1], reverse=True)
            top_files = [{"path": p, "size": s} for p, s in sizes[:10]]
            stats["top_files"] = top_files
        except Exception:
            stats["top_files"] = []

        try:
            stats["contributors"] = _compute_contributors(CLONE_DIR)
        except Exception:
            stats["contributors"] = []

        try:
            stats["dependencies"] = _compute_dependencies(CLONE_DIR)
        except Exception:
            stats["dependencies"] = []

        repo_root = Path(CLONE_DIR)

        try:
            language_insights = compute_language_insights(repo_root)
            stats["language_insights"] = language_insights
            stats["language_insights_summary"] = summarize_language_insights(language_insights)
        except Exception:
            stats["language_insights"] = {}
            stats["language_insights_summary"] = {}

        try:
            stats["architecture_mermaid"] = generate_architecture_mermaid(repo_root)
        except Exception:
            stats["architecture_mermaid"] = ""

        # Persist a snapshot of stats for faster re-use
        try:
            from datetime import datetime
            import json

            cache_dir = Path("./scan_cache")
            cache_dir.mkdir(exist_ok=True)
            repo_name = github_url.rstrip("/").split("/")[-1]
            snapshot = {
                **stats,
                "repo_url": github_url,
                "generated_at": datetime.utcnow().isoformat(),
            }
            with open(cache_dir / f"{repo_name}.json", "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
        except Exception:
            pass

        print(f"""
        📊 Repository Stats:
        - Total Files: {stats['total_files']}
        - Total Chunks: {stats['total_chunks']}
        - Tech Stack: {stats['languages']}
        - Images: {stats['images_processed']}
        """)

        return True, stats

    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        import traceback

        traceback.print_exc()
        return False, {}


# ==============================================================================
# STANDALONE TESTING (Optional)
# ==============================================================================

if __name__ == "__main__":
    """
    Run this file directly to test ingestion without Streamlit.

    Usage:
        python ingest.py
    """

    # Example repository (modify as needed)
    test_repo = "https://github.com/Bhuvangoyal466/EliteThreads"

    print("🚀 Starting repository ingestion pipeline...")
    print(f"Target: {test_repo}\n")

    success, stats = process_repository(test_repo)

    if success:
        print("\n✅ Ingestion successful!")
        print(f"Stats: {stats}")
    else:
        print("\n❌ Ingestion failed. Check errors above.")
