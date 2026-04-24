class EroareUtilitatiRomania(Exception):
    """Eroare de bază pentru integrare."""


class EroareAutentificare(EroareUtilitatiRomania):
    """Autentificare eșuată."""


class EroareConectare(EroareUtilitatiRomania):
    """Eroare temporară de conectare."""


class EroareParsare(EroareUtilitatiRomania):
    """Date neașteptate primite de la furnizor."""


class EroareLicenta(EroareUtilitatiRomania):
    """Licența este invalidă sau lipsește."""


class EroareFurnizorNeimplementat(EroareUtilitatiRomania):
    """Furnizorul există în arhitectură, dar nu este implementat încă."""
