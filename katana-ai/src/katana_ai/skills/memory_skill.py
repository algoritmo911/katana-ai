import os
import requests
import structlog
import uuid

from katana_ai.metrics import LLM_API_ERRORS

# The address of the NeuroVault service, as defined in docker-compose.yml
NEUROVAULT_API_URL = os.environ.get("NEUROVAULT_URL", "http://neurovault:5001")


class QueryMemorySkill:
    """
    A skill that allows Katana to query its long-term memory (NeuroVault).
    """

    def __init__(self, llm_client=None, logger=None):
        """
        Initializes the skill. An LLM client would be injected here.
        """
        self.llm_client = llm_client
        self.log = logger or structlog.get_logger()
        self.log.info("QueryMemorySkill initialized.")

    def execute(self, query: str) -> str:
        """
        Executes the full RAG pipeline from the perspective of Katana.
        """
        log = self.log.bind(query=query)
        log.info("memory_query_executing")

        # 1. Retrieve context from NeuroVault
        try:
            # Get the current trace_id from the contextvars
            trace_id = structlog.contextvars.get_contextvars().get("trace_id")
            headers = {"X-Trace-ID": trace_id} if trace_id else {}

            log.info("neurovault_request_sending", url=f"{NEUROVAULT_API_URL}/retrieve")
            response = requests.post(
                f"{NEUROVAULT_API_URL}/retrieve",
                json={"query": query},
                headers=headers
            )
            response.raise_for_status()
            retrieved_context = response.json().get("context", "")
            log.info("neurovault_request_succeeded")
        except requests.exceptions.RequestException as e:
            log.error("neurovault_connection_failed", error=str(e))
            return "Error: I could not connect to my memory vault."

        if not retrieved_context:
            return "I searched my memory, but couldn't find anything relevant to your question."

        # 2. Synthesize an answer using the context with an LLM
        prompt = self._build_prompt(query, retrieved_context)

        # 2. Synthesize an answer using the context with an LLM
        try:
            # This is where the call to the LLM would happen.
            # We are simulating it for now.
            if self.llm_client:
                # llm_response = self.llm_client.completions.create(...)
                # To simulate an error: raise Exception("LLM API is down")
                pass

            simulated_llm_response = (
                f"Based on my memory, here is what I found about '{query}':\n\n"
                f"{retrieved_context}"
            )
            return simulated_llm_response

        except Exception as e:
            log.error("llm_api_call_failed", error=str(e))
            LLM_API_ERRORS.labels(llm_provider='openai').inc()
            return "I retrieved the relevant information, but failed to generate a summary."


    def _build_prompt(self, query: str, context: str) -> str:
        """Builds the prompt for the LLM."""
        prompt = (
            "You are Katana, a personal AI assistant. "
            "Using the following context, please provide a concise answer to the user's question.\n\n"
            "--- CONTEXT ---\n"
            f"{context}\n"
            "--- END CONTEXT ---\n\n"
            f"User Question: {query}\n\n"
            "Your Answer:"
        )
        log.info("llm_prompt_built")
        return prompt
