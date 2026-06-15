@echo off
title SQL RAG - Install Dependencies
cd /d "%~dp0"
echo ============================================
echo  Installing Dependencies
echo ============================================
echo.

echo Step 1: Install core requirements...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)
echo OK
echo.

echo Step 2: Install tf-keras (fix for SentenceTransformer)...
pip install tf-keras
echo OK
echo.

echo Step 3: Verify key imports...
python -c "import os; os.environ['TF_USE_LEGACY_KERAS']='1'; os.environ['TF_CPP_MIN_LOG_LEVEL']='2'; from sentence_transformers import SentenceTransformer; print('SentenceTransformer OK'); m = SentenceTransformer('BAAI/bge-large-en-v1.5'); print('BGE model loaded OK')"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: SentenceTransformer verification failed.
    echo This might be due to missing PyTorch.
    echo Try: pip install torch --index-url https://download.pytorch.org/whl/cpu
    echo.
) else (
    echo.
    echo All dependencies verified OK.
)
echo.

echo Step 4: Verify Qdrant...
python -c "from qdrant_client import QdrantClient; c=QdrantClient(path='./qdrant_db'); print('Collections:', [col.name for col in c.get_collections().collections])"
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Qdrant verification failed.
) else (
    echo Qdrant OK.
)
echo.

echo ============================================
echo  Installation Complete
echo ============================================
echo.
echo Next steps:
echo 1. Make sure Ollama is running (start_ollama.bat or 'ollama serve')
echo 2. Pull the LLM model: ollama pull qwen2.5:7b
echo 3. Run start_fastapi.bat
echo.
pause
