from xgboost import XGBRegressor
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from nlp_classifier import guess_state
from extractor import links_to_content,scrap_listing
from discord_notifier import send_notifications
import joblib
import os

NB_MAX_PAGE_TO_SEE = 3
MIN_NET_PROFIT = 40.0
EBAY_FEE_RATE = 0.0  # Put 0.12 if you want to include 12% eBay selling fee
SHIPPING_COST = 0.0
DEFAULT_RISK_ERROR = 150.0
RISK_TABLE_PATH = "risk_table.json"

model = XGBRegressor()
model.load_model("tel_xgboost.json")
preprocessor = joblib.load("tel_preprocessor.pkl")

links = set()
SEARCH_QUERIES = [
    "iphone",
    #"iphone 13",
    #"iphone 13 pro",
    #"iphone 13 pro max",

    #"iphone 14",
    #"iphone 14 plus","iphone 14 pro","iphone 14 pro max",
    # "iphone 15",
     #"iphone 15 plus","iphone 15 pro",
    # "iphone 15 pro max",
     #"iphone 16",
    #"iphone 16 plus","iphone 16e",
    #"iphone 16 pro","iphone 16 pro max",
     #"iphone air",
     #"iphone 17",
    #"iphone 17e",
    #"iphone 17 pro","iphone 17 pro max"
    ]


def load_risk_table(filepath: str) -> pd.DataFrame:
    """Load the risk table (MAE/std) calculated in the training"""
    try:
        
        if not os.path.exists(filepath):
            
            return pd.DataFrame()
        return pd.read_json(filepath, orient="index")
    except Exception as e:
        
        return pd.DataFrame()


def get_risk(model_name: str, risk_table: pd.DataFrame) -> float:
    """
    Calculates the financial risk of a prediction.
    Formula: Risk = MAE + (0.5 * std). Applies penalty multipliers if data is scarce.
    """ 
    if risk_table.empty or model_name not in risk_table.index:
        return DEFAULT_RISK_ERROR

    row = risk_table.loc[model_name]
    mae = row['mae']
    std = row['std'] if not np.isnan(row['std']) else 0
    count = row['count']

    risque = mae + 0.5 * std

    if count < 5:
        risque *= 2.0    
    elif count < 10:
        risque *= 1.5
    elif count < 20:
        risque *= 1.2

    return round(risque, 2)

def calcul_benef(row, risk_table: pd.DataFrame) -> float:
    """
    Bénéfice net = prix revente net - risque IA - prix achat
    Prix revente net = prédiction - frais eBay - frais port
    """
    prix_revente_net = row['Predictions'] * (1 - EBAY_FEE_RATE) - SHIPPING_COST
    risque = get_risk(row['Model'], risk_table)
    return prix_revente_net - risque - row['TotalPrice']



def main():
    risk_table = load_risk_table(RISK_TABLE_PATH)

    for query in SEARCH_QUERIES:
        links.update(scrap_listing("historique_en_vente.txt",sold=False,query=query,nb_max_pages=NB_MAX_PAGE_TO_SEE))
        print(f'search finished for {query} ')
    print(f"number of listing found : {len(links)}")

    if links:
            
            df = links_to_content(links, sold=False)
        
            if not df.empty:
                df = df[df["TotalPrice"] > 0]
                df = df.dropna(subset=['Model'])
                df['Model'] = df['Model'].astype(str).str.strip()
                df = df[df["Model"]!=""]
            
                try:
                    df['DescriptionState'] = df["DescriptionStateBrut"].astype(str).str[:450].apply(guess_state)
                    
                except Exception as e:
                    print(f"Error on nlp : {e}")
                try:
                
                    if not df.empty:
                        
                        X = df[['Model', 'Storage', 'Vendor', 'EbayState', 'DescriptionState', 'VendorFeedBacks', 'Battery', 'FaceId', 'Age']]
                        
                        X_live_processed = preprocessor.transform(X)
                    

                        preds = model.predict(X_live_processed)
                    
                        df['Predictions'] = preds
                        df['Risk'] = df['Model'].apply(lambda m: get_risk(m, risk_table))
                        df['Benefices'] = df.apply(lambda row: calcul_benef(row, risk_table), axis=1)
                        
                        
                        to_notify = df[df['Benefices'] >= MIN_NET_PROFIT].sort_values(
                        'Benefices', ascending=False)
                        if not to_notify.empty:
                            
                            for index, row in to_notify.iterrows():
                                try:
                                    send_notifications(
                                        row['Model'], 
                                        row['Link'],
                                        row["DescriptionState"],
                                        row['PhonePrice'], 
                                        row['ShipPrice'], 
                                        row['TotalPrice'], 
                                        row["Benefices"], 
                                        row['Predictions'],
                                        row['Risk']
                                    )
                                except Exception as e:
                                    print(f"Error when sending a notification on discord: {row['Link']} : {e}")
                    else:
                        print("No good price found")
            
                except Exception as e:
                    print(f"Error snipes: {e}")
            else:
                print("no new phones listed")
if __name__ =="__main__":
    main()