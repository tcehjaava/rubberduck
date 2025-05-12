from pathlib import Path


def load_markdown_message(filename: str, **kwargs) -> str:
    file_path = Path(__file__).parent / filename

    with file_path.open("r", encoding="utf-8") as file:
        content = file.read()

    return content.format(**kwargs)


__all__: list[str] = ["load_markdown_message"]
