class AppError(Exception):
    """Error de negocio con mensaje apto para mostrar al usuario."""


class ValidationError(AppError):
    pass


class LimitError(AppError):
    """Se alcanzó un límite de la licencia (modo demo o máximo de la licencia)."""

    def __init__(self, message: str, demo: bool = True):
        super().__init__(message)
        self.demo = demo


class NoCapacityError(AppError):
    pass


class LicenseError(AppError):
    pass
