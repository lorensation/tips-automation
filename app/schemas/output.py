from pydantic import BaseModel


class GeneratedFile(BaseModel):
    output_type: str
    path: str
    checksum: str | None = None
