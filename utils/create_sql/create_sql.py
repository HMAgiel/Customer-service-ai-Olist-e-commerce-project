from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from create_schema import Base, Customer, Order, Payment, Product, Seller, OrderItems


engine = create_engine('sqlite:////home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/sql/olist.db', echo=True)
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)

def seed_customers():
    try:
        df = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/final/olist_customer_dataset_final.csv")
        df["customer_zip_code_prefix"] = df["customer_zip_code_prefix"]
        
        with SessionLocal() as session:
            for _, row in df.iterrows():
                customer = Customer(
                    customer_id = row["customer_id"],
                    customer_unique_id = row["customer_unique_id"],
                    customer_zip_code_prefix = int(row["customer_zip_code_prefix"]) if pd.notna(row["customer_zip_code_prefix"]) else None,
                    customer_city = row["customer_city"],
                    customer_state = row["customer_state"],
                )
                session.add(customer)
            session.commit()
            print("Berhasil memasukan data cutomer ke database sql")
    except ValueError:
        print("Eror data salah")
    except KeyError:
        print("Kolom salah")
            
def seed_seller():
    try:
        df = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/final/olist_sellers_dataset_final.csv")
        
        with SessionLocal() as session:
            for _, row in df.iterrows():
                seller = Seller(
                    seller_id = row["seller_id"],
                    seller_zip_code_prefix = int(row["seller_zip_code_prefix"]) if pd.notna(row["seller_zip_code_prefix"]) else None,
                    seller_city = row["seller_city"],
                    seller_state = row["seller_state"],
                )
                session.add(seller)
            session.commit()
            print("Berhasil memasukkan data seller ke db")
    except ValueError:
        print("Eror data salah")
    except KeyError:
        print("Kolom salah")

def seed_product():
    try:
        df = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/final/olist_product_dataset_final.csv")
        
        with SessionLocal() as session:
            for _, row in df.iterrows():
                product = Product(
                    product_id = row["product_id"],
                    product_category_name = row["product_category_name"],
                    product_photos_qty = int(row["product_photos_qty"]) if pd.notna(row["product_photos_qty"]) else None,
                    product_weight_g = int(row["product_weight_g"]) if pd.notna(row["product_weight_g"]) else None,
                    product_length_cm = int(row["product_length_cm"]) if pd.notna(row["product_length_cm"]) else None,
                    product_height_cm = int(row["product_height_cm"]) if pd.notna(row["product_height_cm"]) else None,
                    product_width_cm = int(row["product_width_cm"]) if pd.notna(row["product_width_cm"]) else None,
                    product_category_name_english = row["product_category_name_english"],
                    product_volume = int(row["product_volume"]) if pd.notna(row["product_volume"]) else None,
                    weight_category = row["weight_category"],
                )
                session.add(product)
            session.commit()
            print("Berhasil menambhakan data product ke db")
        
    except ValueError:
        print("Eror data salah")
    except KeyError:
        print("Kolom salah")
        
def seed_order():
    try:
        df = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/final/olist_orders_dataset_final.csv")
        
        kol_waktu = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]
        for i in kol_waktu:
            df[i] = pd.to_datetime(df[i], errors="coerce")
        
        with SessionLocal() as session:
            for _, row in df.iterrows():
                order = Order(
                    order_id = row["order_id"],
                    customer_id = row["customer_id"],
                    order_status = row["order_status"],
                    order_purchase_timestamp = row["order_purchase_timestamp"].to_pydatetime() if pd.notna(row["order_purchase_timestamp"]) else None,
                    order_approved_at = row["order_approved_at"].to_pydatetime() if pd.notna(row["order_approved_at"]) else None,
                    order_delivered_carrier_date = row["order_delivered_carrier_date"].to_pydatetime() if pd.notna(row["order_delivered_carrier_date"]) else None,
                    order_delivered_customer_date = row["order_delivered_customer_date"].to_pydatetime() if pd.notna(row["order_delivered_customer_date"]) else None,
                    order_estimated_delivery_date = row["order_estimated_delivery_date"].to_pydatetime() if pd.notna(row["order_estimated_delivery_date"]) else None,
                    status_delivered = row["status_delivered"],
                    order_category_status = row["order_category_status"],
                )
                session.add(order)
            session.commit()
            print("Berhasil memasukkan data order ke db")
    except ValueError:
        print("Eror data salah")
    except KeyError as e:
        print(f"Kolom salah, error: {e}")
    

def seed_payment():
    try:
        df = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/final/olist_order_payments_dataset_final.csv")
        
        with SessionLocal() as session:
            for _, row in df.iterrows():
                payment = Payment(
                    order_id = row["order_id"],
                    payment_sequential = int(row["payment_sequential"]) if pd.notna(row["payment_sequential"]) else None,
                    payment_type = row["payment_type"],
                    payment_installments = int(row["payment_installments"]) if pd.notna(row["payment_installments"]) else None,
                    payment_value = float(row["payment_value"]) if pd.notna(row["payment_value"]) else None,
                    payment_id = row["payment_id"],
                )
                session.add(payment)
            session.commit()
            print("Berhasil memasukkan data payment ke db")
    
    except ValueError:
        print("Eror data salah")
    except KeyError:
        print("Kolom salah")
        
def seed_order_item():
    try:
        df = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/final/olist_order_items_dataset_final.csv")
        df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce")
        
        with SessionLocal() as session:
            for _, row in df.iterrows():
                order_items = OrderItems(
                    order_id = row["order_id"],
                    order_item_id = row["order_item_id"],
                    product_id = row["product_id"],
                    seller_id = row["seller_id"],
                    shipping_limit_date = row["shipping_limit_date"].to_pydatetime() if pd.notna(row["shipping_limit_date"]) else None,
                    price = float(row["price"]) if pd.notna(row["price"]) else None,
                    freight_value = float(row["freight_value"]) if pd.notna(row["freight_value"]) else None,
                    total_price = float(row["total_price"]) if pd.notna(row["total_price"]) else None,
                    shipping_category = row["shipping_category"],
                )
                session.add(order_items)
            
            session.commit()
            print("Berhasil memasukkan data order item ke db")
    
    except ValueError:
        print("Eror data salah")
    except KeyError:
        print("Kolom salah")
        

if __name__ == "__main__":
    seed_customers()
    seed_product()
    seed_seller()
    seed_order()
    seed_payment()
    seed_order_item()
    print("Selesai buat database")