from typing import Optional

from pydantic import BaseModel, Field


class ProductSchema(BaseModel):
    product_id: int = Field(..., gt=0)
    name: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category_name: str
    status_name: str
    current_stock: int = Field(..., ge=0)


class ProductSearchResult(BaseModel):
    found: bool
    products: list[ProductSchema] = []
