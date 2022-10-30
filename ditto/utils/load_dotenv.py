try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except ImportError:
    pass