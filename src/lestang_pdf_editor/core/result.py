"""Typed result for operations that can fail without raising.

Résultat typé pour les opérations pouvant échouer sans lever d'exception.
"""

from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok[T]:
    """Successful result wrapping a value.

    Résultat réussi encapsulant une valeur.
    """

    value: T


@dataclass(frozen=True)
class Err[E]:
    """Failed result wrapping an error description.

    Résultat en échec encapsulant une description d'erreur.
    """

    error: E


Result = Ok[T] | Err[E]
"""Either a success value or an error: `Ok[T] | Err[E]`.

Soit une valeur de succès, soit une erreur : `Ok[T] | Err[E]`.
"""
