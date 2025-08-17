from prometheus_client import Counter

LLM_API_ERRORS = Counter(
    'katana_llm_api_errors_total',
    'Total number of errors when calling the LLM API',
    ['llm_provider'] # Label to distinguish different providers, e.g., 'openai'
)
