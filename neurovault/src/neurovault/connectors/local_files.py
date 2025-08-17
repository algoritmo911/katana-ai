import os
from dataclasses import dataclass


@dataclass
class Document:
    """A simple data class to hold document information."""
    id: str  # Unique identifier, e.g., file path
    content: str
    metadata: dict


class LocalFileConnector:
    """
    Connects to the local filesystem to find and read source documents.
    """

    def __init__(self, source_path: str):
        if not os.path.isdir(source_path):
            raise ValueError(f"Source path does not exist or is not a directory: {source_path}")
        self.source_path = source_path

    def get_documents(self) -> list[Document]:
        """
        Scans the source directory for .md files and returns their content.
        """
        documents = []
        for root, _, files in os.walk(self.source_path):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Use the relative path as the document ID for consistency
                        relative_path = os.path.relpath(file_path, self.source_path)

                        doc = Document(
                            id=relative_path,
                            content=content,
                            metadata={
                                "source": "local_filesystem",
                                "full_path": file_path,
                                "filename": file,
                                "size_bytes": os.path.getsize(file_path)
                            }
                        )
                        documents.append(doc)
                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")

        print(f"Found {len(documents)} markdown documents in {self.source_path}")
        return documents
