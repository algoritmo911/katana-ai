import io
import requests
from PyPDF2 import PdfReader, PdfWriter

class PochtaClient:
    """
    A client for interacting with pochta-opis.ru services,
    specifically for generating 'Form 107' (opis vложения).
    """
    BLANK_FORM_URL = "https://pochta-opis.ru/static/blank.pdf"

    def get_blank_form(self) -> io.BytesIO:
        """Downloads the blank PDF form."""
        try:
            response = requests.get(self.BLANK_FORM_URL)
            response.raise_for_status()
            return io.BytesIO(response.content)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading the form: {e}")
            return None

    def get_form_fields(self, pdf_stream: io.BytesIO) -> dict:
        """Reads a PDF stream and returns a dictionary of its form fields."""
        if not pdf_stream:
            return {}
        pdf_stream.seek(0)
        reader = PdfReader(pdf_stream)
        if reader.get_fields() is None:
            return {}
        return reader.get_fields()

    def create_opis(self, items: list, sender_address: str, output_path: str):
        """
        Generates a filled 'Form 107' PDF.

        :param items: A list of dictionaries, where each dictionary
                      represents an item and has keys 'name', 'quantity', 'value'.
                      The list can have a maximum of 14 items.
        :param sender_address: The sender's full name and address (use '\\n' for new lines).
        :param output_path: The path to save the filled PDF file.
        """
        pdf_stream = self.get_blank_form()
        if not pdf_stream:
            print("Could not download the form.")
            return

        reader = PdfReader(pdf_stream)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)

        # The field names have a long, static suffix which we need to use.
        field_suffix = "_dfaf011e-5c63-471c-967d-36f529ef3af6_ffb4c15e-30bf-484e-bce9-6373e51c7d05"

        fields_to_update = {}
        total_count = 0
        total_value = 0

        # Populate item fields
        for i, item in enumerate(items):
            if i >= 14:
                print("Warning: More than 14 items provided. Only the first 14 will be included.")
                break

            row = i + 1
            item_value = item.get('value', 0)
            item_quantity = item.get('quantity', 0)

            # Fill fields for both forms (1 and 2) on the page
            for form_num in [1, 2]:
                fields_to_update[f"ItemID_{form_num}_{row}{field_suffix}"] = str(row)
                fields_to_update[f"ItemName_{form_num}_{row}{field_suffix}"] = item.get('name', '')
                fields_to_update[f"ItemCount_{form_num}_{row}{field_suffix}"] = str(item_quantity)
                fields_to_update[f"ItemCost_{form_num}_{row}{field_suffix}"] = str(item_value)

            total_count += item_quantity
            total_value += item_value

        # Populate total fields
        for form_num in [1, 2]:
            fields_to_update[f"ItemTotalCount_{form_num}_1{field_suffix}"] = str(total_count)
            fields_to_update[f"TotalCost_{form_num}_1{field_suffix}"] = str(total_value)

        # Populate sender fields (assuming it's a multi-line field split into two parts)
        sender_lines = sender_address.split('\n')
        for form_num in [1, 2]:
            fields_to_update[f"Sender_{form_num}_1{field_suffix}"] = sender_lines[0] if len(sender_lines) > 0 else ""
            fields_to_update[f"Sender_{form_num}_2{field_suffix}"] = sender_lines[1] if len(sender_lines) > 1 else ""

        # Update the fields in the writer
        writer.update_page_form_field_values(writer.pages[0], fields_to_update)

        # Write the output file
        try:
            with open(output_path, "wb") as output_stream:
                writer.write(output_stream)
            print(f"Successfully created filled form at {output_path}")
        except IOError as e:
            print(f"Error writing the output file: {e}")


if __name__ == '__main__':
    client = PochtaClient()

    print("\n---")
    print("Generating a sample opis form...")

    # Define the sender and the items to be listed
    sender = "Иванов Иван Иванович\\nг. Москва, ул. Ленина, д. 1, кв. 1"
    items_to_send = [
        {'name': 'Документы (договор, акт)', 'quantity': 1, 'value': 1000},
        {'name': 'Книга "Искусство программирования"', 'quantity': 1, 'value': 2500},
        {'name': 'USB-накопитель 64ГБ', 'quantity': 2, 'value': 500},
    ]

    client.create_opis(
        items=items_to_send,
        sender_address=sender,
        output_path="opis_filled.pdf"
    )
