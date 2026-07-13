from typing import Optional

from pydantic import BaseModel, Field


class ProductSchema(BaseModel):
    product_id: int = Field(..., gt=0) # Identificador único del producto.
    name: str = Field(..., max_length=200) # Nombre del producto.
    description: Optional[str] = Field(default=None, max_length=1000) # Descripción del producto, puede ser nula si no se proporciona.
    price: float = Field(..., ge=0) # Precio del producto.
    category_name: str = Field(..., max_length=100) # Nombre de la categoría.
    status_name: str = Field(..., max_length=100) # Nombre del estado.
    current_stock: int = Field(..., ge=0) # Stock disponible.


class ProductSearchResult(BaseModel):
    found: bool # Indica si se encontraron productos que coincidan con la búsqueda.
    products: list[ProductSchema] = [] # Lista de productos encontrados. Puede estar vacía si no se encontraron coincidencias.
