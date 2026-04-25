from fastapi import HTTPException, status

class FileProcessingError(HTTPException):
    def __init__(self, detail: str = "Error processing file"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

class ParsingError(FileProcessingError):
    def __init__(self, detail: str = "Could not extract tables from PDF. Might be scanned."):
        super().__init__(detail=detail)

class NoDataFoundError(FileProcessingError):
    def __init__(self):
        super().__init__(detail="No valid transactions found in the document.")