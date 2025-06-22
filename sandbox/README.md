# Sandbox Environment

This directory is intended for experimentation, prototyping, and testing new ideas or features before integrating them into the main application.

## Purpose

-   **Rapid Prototyping:** Quickly build and test new functionalities, especially those involving external services or complex logic.
-   **AI SDK Integration Tests:** Experiment with different AI SDKs (OpenAI, Anthropic, HuggingFace, etc.), test various models, and fine-tune prompts.
-   **Async Experiments:** Test asynchronous patterns and performance optimizations in isolation.
-   **Exploring New Libraries:** Try out new Python libraries or tools that could be beneficial for the project.

## Guidelines

-   Code in this directory is not expected to be production-ready.
-   Feel free to create subdirectories for different experiments.
-   Scripts here can be run independently.
-   It's a good practice to document what each script or module in the sandbox does, perhaps with a small comment at the top of the file or a more detailed README if the experiment is complex.
-   Ensure that API keys or sensitive credentials are not hardcoded. Use environment variables (e.g., via a `.env` file loaded by `python-dotenv` in your sandbox script) similar to the main application.

## Example Usage

You might create a script like `sandbox/test_openai_vision.py` to experiment with OpenAI's vision models, or `sandbox/try_new_vector_db.py` to explore a new vector database.

To run a script:
```bash
python sandbox/your_script_name.py
```

Remember to install any new dependencies required by your sandbox scripts. You might manage these locally or temporarily add them to the main `requirements.txt` if they are likely to be integrated.
