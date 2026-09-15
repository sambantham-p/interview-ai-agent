QUESTION_EMBEDDING_DIM = 768

EMBEDDING_MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"

# Top-k pulled once at interview-start (~10-15 questions ).
QUESTION_POOL_TOP_K = 35

# Maximum cosine distance for JD relevance (0 = identical, 2 = opposite).
# Questions beyond it are excluded; tune as retrieval coverage improves.
QUESTION_POOL_MAX_COSINE_DISTANCE = 0.8

QUESTIONS_PER_PHASE = 5

QUESTION_BANK_PHASES = ["technical_interview", "coding_challenge", "general_technical"]
