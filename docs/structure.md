## query flow

```
User Question
     ↓
Embedding (OpenAI)
     ↓
Vector Search (ChromaDB)
     ↓
Relevant Chunks
     ↓
LLM Prompt (Context + Question)
     ↓
Answer

```
