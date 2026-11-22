"""CLI entry point; prints the version until the UI is implemented.

Point d'entrée CLI ; affiche la version en attendant l'UI.
"""

from docscanner import __version__


def main() -> None:
    """Print the app name and version.

    Affiche le nom et la version de l'application.
    """
    print(f"Doc Scan PDF Editor {__version__}")


if __name__ == "__main__":
    main()
