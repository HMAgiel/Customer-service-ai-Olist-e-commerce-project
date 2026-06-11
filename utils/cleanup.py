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
data[7].to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_geolocation_dataset.csv', index=False) #Simpan sebagai csv
#ubah ke dictionary untuk mapping file lain
loc_fix = pd.read_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_geolocation_dataset_clean.csv')
lokasi_zip = loc_fix.drop(columns=['geolocation_lat', 'geolocation_lng', 'geolocation_state']).set_index('geolocation_zip_code_prefix')['geolocation_city'].to_dict()

#Bersihkan data seller dan isi yang kosong dan aneh
data_seller = data[4].copy()
data_seller['seller_city_fix'] = data_seller['seller_zip_code_prefix'].map(lokasi_zip)
data_seller['seller_city'] = data_seller['seller_city_fix'].combine_first(data_seller['seller_city'])['seller_city'] = data_seller['seller_city_fix'].combine_first(data_seller['seller_city'])
data_seller2 = data_seller.drop(columns=["seller_city_fix"])
data_seller2.to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_sellers_dataset_celan.csv', index=False)

#Bersihkan data review dan ubah format tanggal agar standar
kol_tanggal = ['review_creation_date', 'review_answer_timestamp']
kol_review = ['review_comment_title', 'review_comment_message']
data[0][kol_tanggal] = data[0][kol_tanggal].apply(pd.to_datetime, format='%Y-%m-%d %H:%M:%S')
for i in kol_review:
    data[0][i] = data[0][i].apply(normalize)
data[0].to_csv('/home/hasyim/final_project/Repo-Final-Project-Kelompok-3/data/process/olist_order_reviews_dataset_clean.csv', index=False)
