import pandas as pd
from uuid import uuid4

#ubah ke dictionary untuk mapping file lain
loc_fix = pd.read_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_geolocation_dataset_clean.csv')
lokasi_zip = loc_fix.drop(columns=['geolocation_lat', 'geolocation_lng', 'geolocation_state']).set_index('geolocation_zip_code_prefix')['geolocation_city'].to_dict()


def fix_loc(path, kota, zip_code, nama_file):
    data = pd.read_csv(path)
    data['temp_loc_fix'] = data[zip_code].map(lokasi_zip)
    data[kota] = data['temp_loc_fix'].combine_first(data[kota])
    data = data.drop(columns=["temp_loc_fix"])
    data.to_csv(f'/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/final/{nama_file}.csv', index=False)

#fix data seller
seller_path = "/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_sellers_dataset_clean.csv"
fix_loc(seller_path, "seller_city", "seller_zip_code_prefix", "olist_sellers_dataset_final")

#fix data customer
cust_path = "/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_customer_dataset_clean.csv"
fix_loc(cust_path, "customer_city", "customer_zip_code_prefix", "olist_customer_dataset_final")


#fix and feature engineering product data
product_data = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_product_dataset_clean.csv")
product_english_data = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_product_category_dataset_clean.csv")
product_english = product_english_data.set_index('product_category_name')['product_category_name_english'].to_dict()
product_data = product_data.drop(columns=["product_name_lenght", "product_description_lenght"])
product_data["product_photos_qty"] = product_data["product_photos_qty"].fillna(0)

kolom_cat = ['product_category_name']
kol_num = ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
for i in kolom_cat:
    product_data[i] = (
        product_data.groupby(
            kol_num,
            dropna=False
        )[i].transform(
            lambda x: x.fillna(x.mode().iloc[0])
            if not x.mode().empty else x
        )
    )
product_data = product_data.dropna()
product_data["product_category_name_english"] = product_data["product_category_name"].map(product_english)
product_data["product_category_name_english"] = product_data["product_category_name_english"].fillna("Unknow")
product_data["product_volume"] = product_data["product_length_cm"] * product_data["product_height_cm"] * product_data["product_width_cm"]

def weight_category(berat):
    if berat <= 1000:
        return "light"
    elif berat <= 3000:
        return "medium"
    elif berat <= 10000:
        return "heavy"
    else:
        return "very heavy"
    
product_data["weight_category"] = product_data["product_weight_g"].apply(weight_category)
product_data.to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/final/olist_product_dataset_final.csv', index=False)

#order data 
order_data = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/raw/olist_orders_dataset.csv")
kol_waktu_order = ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date', 'order_delivered_customer_date', 'order_estimated_delivery_date']
order_data[kol_waktu_order] = order_data[kol_waktu_order].apply(pd.to_datetime, format='mixed')

order_data['time_different'] = (order_data["order_delivered_customer_date"] - order_data["order_estimated_delivery_date"]).dt.days

def delivered_satatus(time):
    if time <= 0:
        return "on time"
    elif time > 0:
        return "late"
    else:
        return "not arrived"

order_data["status_delivered"] = order_data["time_different"].apply(delivered_satatus)

def delivery_group_status(status):
    if status == "delivered":
        return "success"
    elif status == ['invoiced', 'shipped', 'processing', 'created', 'approved']:
        return "in progress"
    else:
        return "failed"

order_data["order_category_status"] = order_data["order_status"].apply(delivery_group_status)
order_data = order_data.drop(columns=["time_different"])
order_data.to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/final/olist_orders_dataset_final.csv', index=False)


#frature engineering order items data
ordr_item_data = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/raw/olist_order_items_dataset.csv")

ordr_item_data['total_price'] = ordr_item_data['price'] +  ordr_item_data['freight_value']

def shipping_price_caategory(ongkir):
    if ongkir == 0:
        return "free shipping"
    elif ongkir > 0 and ongkir <= 15:
        return "cheap"
    elif ongkir > 15 and ongkir <=35:
        return "standard"
    elif ongkir > 35 and ongkir <= 70:
        return "expensive"
    else:
        return "very expensive"

ordr_item_data["shipping_category"] = ordr_item_data["freight_value"].apply(shipping_price_caategory)
ordr_item_data["order_item_id"] = [uuid4().hex for _ in range(len(ordr_item_data["order_item_id"]))]
ordr_item_data.to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/final/olist_order_items_dataset_final.csv', index=False)

# add id to payment
payment = pd.read_csv("/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/raw/olist_order_payments_dataset.csv")
payment["payment_id"] = [uuid4().hex for _ in range(len(payment))]
payment.to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/final/olist_order_payments_dataset_final.csv', index=False)