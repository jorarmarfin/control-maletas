class AppError(Exception):
    """Error de negocio con mensaje apto para mostrar al usuario."""


class ValidationError(AppError):
    pass


class LimitError(AppError):
    """Se alcanzó un límite de la licencia (modo demo o máximo de la licencia)."""


class NoCapacityError(AppError):
    pass


class LicenseError(AppError):
    pass
