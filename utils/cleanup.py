import glob
import pandas as pd
import numpy as npp
import matplotlib.pyplot as plt
import os
import unicodedata
import re

path = "/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/raw"

data_path = glob.glob(f"{path}/*.csv")

data = []
miss = []
for i in data_path:
    buka_data = pd.read_csv(i)
    missing = buka_data.isna().sum()
    data.append(buka_data)
    miss.append(missing)

#normalisasi data menghilangkan aksen yang bukan kata latin
def normalize(data):
    if not isinstance(data, str):
        return data
    kata = unicodedata.normalize('NFKD', data)
    kata_normal = ''.join([i for i in kata if not unicodedata.combining(i)])
    return kata_normal

#Normalisasikan geolocation untuk referensi
data[7]['geolocation_city'] = data[7]['geolocation_city'].apply(normalize)
data[7].to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_geolocation_dataset_clean.csv', index=False) #Simpan sebagai csv

#Bersihkan data cutomer
data[3]['customer_city'] = data[3]['customer_city'].apply(normalize)
data[3].to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_customer_dataset_clean.csv', index=False)

#Bersihkan data seller dan isi yang kosong dan aneh
data[4]['seller_city'] = data[4]['seller_city'].apply(normalize)
data[4].to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_sellers_dataset_clean.csv', index=False)

#Bersihkan aksen di produk
data[6]['product_category_name'] = data[6]['product_category_name'].apply(normalize)
data[6].to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_product_dataset_clean.csv', index=False)

#Bersihkan nama di kategori
data[2]['product_category_name'] = data[2]['product_category_name'].apply(normalize)
data[2].to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_product_category_dataset_clean.csv', index=False)

#Bersihkan data review dan ubah format agar standar
kol_review = ['review_comment_title', 'review_comment_message']
for i in kol_review:
    data[0][i] = data[0][i].apply(normalize)
data[0].to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_order_reviews_dataset_clean.csv', index=False)

