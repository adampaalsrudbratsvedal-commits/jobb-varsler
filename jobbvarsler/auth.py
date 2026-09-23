"""Engangs innlogging mot Gmail (åpner nettleseren)."""

from . import gmail


def main() -> None:
    service = gmail.get_service(interactive=True)
    print(f"Innlogget som {gmail.get_profile_email(service)}. Tokenet er lagret i data/token.json.")
