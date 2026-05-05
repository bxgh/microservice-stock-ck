class DataMismatchException(Exception):
    """
    Raised when data consistency check fails (e.g., source count != target count).
    """
    def __init__(self, message: str, source_count: int, target_count: int):
        self.message = message
        self.source_count = source_count
        self.target_count = target_count
        super().__init__(self.message)
