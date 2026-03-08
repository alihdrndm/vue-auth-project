"""Errors raised by the einvoice package. None of them carry document contents."""


class EinvoiceError(Exception):
    """Base class for every error this package raises on purpose."""


class UnsupportedFileError(EinvoiceError):
    """The bytes are not a file Eingang accepts (API: 415 UNSUPPORTED_FILE)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class UnsafeXmlError(UnsupportedFileError):
    """The XML contains a DOCTYPE, which could declare external or expanding entities."""

    def __init__(self) -> None:
        super().__init__("XML with a DOCTYPE declaration is not accepted")


class InvoiceParseError(EinvoiceError):
    """A required field is missing or a value cannot be read."""

    def __init__(self, field: str, path: str, problem: str = "is missing") -> None:
        super().__init__(f"{field} {problem} (at {path})")
        self.field = field
        self.path = path
        self.problem = problem
