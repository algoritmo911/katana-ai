class DialogueContextManager:
    """
    Manages the dialogue context, including entity merging for follow-up questions.
    """
    def get_initial_session(self):
        """Returns the initial structure for a new session."""
        return {"context": {"entities": {}}, "history": []}

    def update_context(self, current_context: dict, nlp_result: dict) -> dict:
        """
        Updates the context based on the latest NLP analysis.
        This is where the logic for dialogue continuation lives.
        """
        dialogue_state = nlp_result.get("metadata", {}).get("raw_openai_response", {}).get("dialogue_state", "new_request")
        new_entities = nlp_result.get("entities", {})

        if dialogue_state == "continuation":
            # Merge new entities into the existing context
            updated_entities = current_context.get("entities", {}).copy()
            updated_entities.update(new_entities)
            return {"entities": updated_entities}
        else:
            # It's a new request, so we start with a fresh entity context
            return {"entities": new_entities}
