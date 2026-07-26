from pydantic import BaseModel


class HexModel(BaseModel):
    h3_index: str
    level: int
    cell_id: int

    def as_list(self) -> list[str | int]:
        return [self.h3_index, self.level, self.cell_id]
