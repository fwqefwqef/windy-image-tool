try:
    import pillow_avif  # noqa: F401 — registers AVIF support when bundled
except ImportError:
    pass

from app import run

if __name__ == "__main__":
    run()
