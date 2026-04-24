from __future__ import annotations

from abc import ABC, abstractmethod
from aiohttp import ClientSession

from ..modele import InstantaneuFurnizor


class ClientFurnizor(ABC):
    cheie_furnizor: str = "baza"
    nume_prietenos: str = "Bază"

    def __init__(self, *, sesiune: ClientSession, utilizator: str, parola: str, optiuni: dict) -> None:
        self.sesiune = sesiune
        self.utilizator = utilizator
        self.parola = parola
        self.optiuni = optiuni

    @abstractmethod
    async def async_testeaza_conexiunea(self) -> str:
        pass

    @abstractmethod
    async def async_obtine_instantaneu(self) -> InstantaneuFurnizor:
        pass
