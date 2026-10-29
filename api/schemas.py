from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class CustomerCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=40)
    customer_unique_id: Optional[str] = Field(default=None, max_length=40)
    customer_city: Optional[str] = Field(default=None, max_length=100)
    customer_state: Optional[str] = Field(default=None, min_length=2, max_length=2)


class CustomerUpdate(BaseModel):
    customer_unique_id: Optional[str] = Field(default=None, max_length=40)
    customer_city: Optional[str] = Field(default=None, max_length=100)
    customer_state: Optional[str] = Field(default=None, min_length=2, max_length=2)

    @model_validator(mode="after")
    def require_one_field(self):
        if self.customer_unique_id is None and self.customer_city is None and self.customer_state is None:
            raise ValueError("Provide at least one field to update")
        return self


class ProductCreate(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=40)
    product_category_name: Optional[str] = Field(default=None, max_length=100)
    product_name_lenght: Optional[int] = None
    product_description_lenght: Optional[int] = None
    product_photos_qty: Optional[int] = None
    product_weight_g: Optional[int] = None
    product_length_cm: Optional[int] = None
    product_height_cm: Optional[int] = None
    product_width_cm: Optional[int] = None


class ProductUpdate(BaseModel):
    product_category_name: Optional[str] = Field(default=None, max_length=100)
    product_name_lenght: Optional[int] = None
    product_description_lenght: Optional[int] = None
    product_photos_qty: Optional[int] = None
    product_weight_g: Optional[int] = None
    product_length_cm: Optional[int] = None
    product_height_cm: Optional[int] = None
    product_width_cm: Optional[int] = None

    @model_validator(mode="after")
    def require_one_field(self):
        if all(getattr(self, name) is None for name in self.model_fields):
            raise ValueError("Provide at least one field to update")
        return self


class OrderItemIn(BaseModel):
    order_item_id: int = Field(..., ge=1)
    product_id: Optional[str] = None
    seller_id: Optional[str] = None
    price: float = Field(..., ge=0)
    freight_value: Optional[float] = Field(default=None, ge=0)


class OrderItemCreate(OrderItemIn):
    order_id: str = Field(..., min_length=1, max_length=40)


class OrderItemUpdate(BaseModel):
    product_id: Optional[str] = None
    seller_id: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    freight_value: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_one_field(self):
        if self.product_id is None and self.seller_id is None and self.price is None and self.freight_value is None:
            raise ValueError("Provide at least one field to update")
        return self


class OrderCreate(BaseModel):
    order_id: str = Field(..., min_length=1, max_length=40)
    customer_id: str = Field(..., min_length=1, max_length=40)
    order_status: str = Field(default="created", max_length=30)
    order_purchase_timestamp: datetime
    items: list[OrderItemIn] = Field(default_factory=list)


class OrderUpdate(BaseModel):
    customer_id: Optional[str] = Field(default=None, max_length=40)
    order_status: Optional[str] = Field(default=None, max_length=30)
    order_purchase_timestamp: Optional[datetime] = None

    @model_validator(mode="after")
    def require_one_field(self):
        if self.customer_id is None and self.order_status is None and self.order_purchase_timestamp is None:
            raise ValueError("Provide at least one field to update")
        return self
