import uuid
from datetime import datetime

import pandas as pd
from sqlalchemy import ForeignKey, String,Integer, Float, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Customer(Base):
    __tablename__ = "customers"
    customer_id : Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    customer_unique_id : Mapped[str] = mapped_column(String(32), default=lambda: uuid.uuid4().hex)
    customer_city : Mapped[str] = mapped_column(String)
    customer_state : Mapped[str] = mapped_column(String)
    
    orders : Mapped[list["Order"]] = relationship("Order", back_populates="customer")
    
class Order(Base):
    __tablename__ = "orders"
    order_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    order_status: Mapped[str] = mapped_column(String)
    order_purchase_timestamp: Mapped[datetime] = mapped_column(DateTime)
    order_approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    order_delivered_carrier_date: Mapped[datetime | None] = mapped_column(DateTime)
    order_delivered_customer_date: Mapped[datetime | None] = mapped_column(DateTime)
    order_estimated_delivery_date: Mapped[datetime| None] = mapped_column(DateTime)
    status_delivered: Mapped[str] = mapped_column(String)
    order_category_status: Mapped[str] = mapped_column(String)
    
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    payment: Mapped[list["Payment"]] = relationship("Payment", back_populates="order_payment")
    order_items : Mapped[list["OrderItems"]] = relationship("OrderItems", back_populates="order")
    order_review : Mapped[list["Review"]] = relationship("Review", back_populates="review_order")
    
class Payment(Base):
    __tablename__ = "payments"
    payment_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"))
    payment_sequential: Mapped[int | None] = mapped_column(Integer)
    payment_type: Mapped[str] = mapped_column(String)
    payment_installments: Mapped[int | None] = mapped_column(Integer)
    payment_value: Mapped[float | None] = mapped_column(Float)
    
    order_payment : Mapped["Order"] = relationship("Order", back_populates="payment")
    
class Product(Base):
    __tablename__ = "product"
    product_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    product_category_name: Mapped[str] = mapped_column(String)
    product_photos_qty: Mapped[int | None] = mapped_column(Integer)
    product_weight_g: Mapped[int | None] = mapped_column(Integer)
    product_length_cm: Mapped[int | None] = mapped_column(Integer)
    product_height_cm: Mapped[int | None] = mapped_column(Integer)
    product_width_cm: Mapped[int | None] = mapped_column(Integer)
    product_volume: Mapped[int | None] = mapped_column(Integer)
    weight_category: Mapped[str] = mapped_column(String)
    
    order_products : Mapped[list["OrderItems"]] = relationship("OrderItems", back_populates="order_product")
    
class Seller(Base):
    __tablename__ = "seller"
    seller_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    seller_zip_code_prefix: Mapped[int | None] = mapped_column(Integer)
    seller_city: Mapped[str] = mapped_column(String)
    seller_state: Mapped[str] = mapped_column(String)
    
    order_sellers : Mapped[list["OrderItems"]] = relationship("OrderItems", back_populates="order_seller")
    
class OrderItems(Base):
    __tablename__ = "order_items"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"))
    order_item_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    product_id: Mapped[str] = mapped_column(ForeignKey("product.product_id"))
    seller_id: Mapped[str] = mapped_column(ForeignKey("seller.seller_id"))
    shipping_limit_date: Mapped[datetime] = mapped_column(DateTime)
    price: Mapped[float | None] = mapped_column(Float)
    freight_value: Mapped[float | None] = mapped_column(Float)
    total_price: Mapped[float | None] = mapped_column(Float)
    shipping_category: Mapped[str] = mapped_column(String)
    
    order : Mapped["Order"] = relationship("Order", back_populates="order_items")
    order_product : Mapped["Product"] = relationship("Product", back_populates="order_products")
    order_seller : Mapped["Seller"] = relationship("Seller", back_populates="order_sellers")
    
class Review(Base):
    __tablename__ = "review"
    review_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"))
    review_score: Mapped[int | None] = mapped_column(Integer)
    
    review_order: Mapped["Order"] = relationship("Order", back_populates="order_review")
    