from typing import Optional

from pydantic import BaseModel


class ProductSchema(BaseModel):
    product_id: int
    name: str
    description: Optional[str] = None
    price: float
    category_name: str
    status_name: str
    current_stock: int


class ProductSearchResult(BaseModel):
    found: bool
    products: list[ProductSchema] = []