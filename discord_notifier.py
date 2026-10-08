import requests
import os
from dotenv import load_dotenv
load_dotenv()

url_discord = os.getenv("URL_DISCORD")

def send_notifications(title:str,url:str,state:str,price:float,ship_price:float,total_price:float,benefice:float,predicted_price:float,risk:float):
    colis_json = {"embeds":[
        {"title":title,
        "description":f"etat:{state}\nprix tel : {price}€\nprix frais : {ship_price}\nprix total: {total_price}€\nprix prédit: {predicted_price}\nbenefice : {benefice}€\nrisque: {risk}",
        "url":url}
        ]
                }
    header = {"Content-Type": "application/json"}

    response =requests.post(url_discord,json=colis_json,headers=header)
    print(response.status_code)
    print(response.text)
