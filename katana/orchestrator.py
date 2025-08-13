# katana/orchestrator.py

from katana.integrations.pochta_client import PochtaClient

class Orchestrator:
    """
    A simple orchestrator to manage and provide access to various 'Capabilities'.
    """
    def __init__(self):
        self._capabilities = {}
        self._register_default_capabilities()

    def _register_default_capabilities(self):
        """
        Initializes and registers the default clients/capabilities.
        """
        # Register the PochtaClient
        pochta_client = PochtaClient()
        self.register_capability("pochta_opis", pochta_client)

    def register_capability(self, name: str, instance):
        """
        Registers a new capability (client instance).
        """
        print(f"Registering capability: {name}")
        self._capabilities[name] = instance

    def get_capability(self, name: str):
        """
        Retrieves a registered capability by its name.
        """
        return self._capabilities.get(name)

    def list_capabilities(self) -> list:
        """
        Returns a list of the names of all registered capabilities.
        """
        return list(self._capabilities.keys())

if __name__ == '__main__':
    # --- Example of using the Orchestrator ---
    print("Initializing Orchestrator...")
    orchestrator = Orchestrator()

    print("\nAvailable capabilities:")
    print(orchestrator.list_capabilities())

    # Get the pochta client from the orchestrator
    pochta_service = orchestrator.get_capability("pochta_opis")

    if pochta_service:
        print("\nSuccessfully retrieved 'pochta_opis' capability.")
        print("Using the service to generate a form...")

        # Use the retrieved client to perform an action
        sender = "Петров Петр Петрович\\nг. Санкт-Петербург, Невский пр., д. 10"
        items = [
            {'name': 'Смартфон', 'quantity': 1, 'value': 20000},
            {'name': 'Чехол для смартфона', 'quantity': 1, 'value': 500},
        ]

        pochta_service.create_opis(
            items=items,
            sender_address=sender,
            output_path="orchestrator_test_opis.pdf"
        )
    else:
        print("\nCould not retrieve 'pochta_opis' capability.")
