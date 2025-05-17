
class ApplicationError(Exception):
    """Base class for application-specific errors."""
    pass

class ProductNotFoundError(ApplicationError):
    """Raised when a product is not found."""
    pass

class ProductAlreadyExistsError(ApplicationError):
    """Raised when attempting to create a product that already exists."""
    pass

class DatabaseError(ApplicationError):
    """Raised for general database-related errors not specifically handled."""
    def __init__(self, message="A database error occurred.", original_exception=None):
        super().__init__(message)
        self.original_exception = original_exception
