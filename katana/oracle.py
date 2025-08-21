import logging
import re
from typing import Optional

from katana.memory.core import MemoryCore
from katana.agents.specialists import PriceAgent, WebSearchAgent, SummarizerAgent

# Initialize logger
logger = logging.getLogger(__name__)

class Oracle:
    """
    The Oracle orchestrates a swarm of specialist agents to answer complex questions.
    """
    def __init__(self, memory: Optional[MemoryCore] = None):
        """
        Initializes the Oracle.

        Args:
            memory: An optional MemoryCore instance to provide memory to the agents.
        """
        self.memory = memory
        logger.info("Oracle initialized.")

    def query(self, question: str) -> str:
        """
        Answers a question by orchestrating a sequence of specialist agents.

        For this initial implementation, it follows a hardcoded plan for questions like:
        "What is the price of BTC-USD and what is the latest news?"

        Args:
            question: The user's question.

        Returns:
            A synthesized answer.
        """
        logger.info(f"Oracle received a new query: '{question}'")

        # --- Phase 1: Planning (currently hardcoded) ---
        # A more advanced Oracle would dynamically generate this plan.
        # For now, we use regex to see if it's a query we can handle.

        match = re.search(r"price of ([\w-]+)", question, re.IGNORECASE)
        if not match:
            logger.warning("Query does not match the hardcoded plan. Returning a default response.")
            return "I can currently only answer questions about the price and news of a specific asset, like 'What is the price of BTC-USD and what is the latest news?'"

        asset = match.group(1).upper()
        logger.info(f"Plan: 1. Get price for {asset}. 2. Get news for {asset}. 3. Summarize.")

        # --- Phase 2: Execution ---
        # Instantiate the required agents
        price_agent = PriceAgent(memory=self.memory)
        search_agent = WebSearchAgent(memory=self.memory)
        summarizer_agent = SummarizerAgent(memory=self.memory)

        # 1. Get price
        price_task = {"action": "get_spot_price", "product_id": asset}
        price_result = price_agent.execute(price_task)
        price_info = f"The price of {asset} is {price_result.get('price')} {price_result.get('currency')}." if isinstance(price_result, dict) and 'price' in price_result else f"Could not retrieve the price for {asset}."
        logger.info(f"Price Agent result: {price_info}")

        # 2. Get news
        search_task = {"action": "web_search", "query": f"{asset} crypto news"}
        search_result = search_agent.execute(search_task)
        news_info = f"Web search results: {search_result.get('results')}" if isinstance(search_result, dict) and 'results' in search_result else "Could not retrieve news."
        logger.info(f"Web Search Agent result: {news_info}")

        # --- Phase 3: Synthesis ---
        combined_information = f"Price Information: {price_info}\n\nNews Information: {news_info}"

        summarize_task = {
            "action": "summarize_text",
            "text": combined_information,
            "user_prompt": question
        }
        final_answer = summarizer_agent.execute(summarize_task)

        logger.info(f"Oracle finished processing query. Final answer: {final_answer}")
        return final_answer
