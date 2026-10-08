"""Scraper module for eBay listings.
Extracts phone features (model, storage, condition, price) from active or sold listings."""

from playwright.sync_api import sync_playwright
from datetime import datetime
import pandas as pd
import random as rd
import unicodedata
import time
import re
import os

EBAY_LINK = "https://www.ebay.fr/"
ACCESSORY_WORDS = r'\b(coque|bouton|dock|support|magsafe|powerbank|batterie externe|boite vide|boîte vide|vide|case|cover|bumper|otterbox|verre trempé|verre trempe|glass|câble|cable|chargeur|étui|etui|dummy|factice|housse|protection|wallet)\b'
FORBIDDEN_WORDS = r'\b(dalle|cadre|battery iphone|batterie iphone|haut parleur|haut-parleur|in-cell|in cell|connecteur|remplacement|outil|outils|kit|vitre arriere|nappe|lentille|camera|lot coque|reparation|ecran oled|ecran lcd|oled|ecran gx|tools|ecran comp|android|bloc ecran|cache arriere|cache batterie|vitre tactile|chassis|châssis|façade|facade|carte mere|motherboard|batterie neuve|boite vide|dummy|factice|empty box|icloud|bloque|mdm|activation lock|pour pieces|hs)\b'
PHONE_CREATION_YEAR = {
        'iphone 4': 2010, 'iphone 5': 2012, 'iphone 6': 2014, 
        'iphone 7': 2016, 'iphone 7 plus': 2016, 'iphone 8': 2017, 'iphone 8 plus': 2017,
        'iphone x': 2017, 'iphone xr': 2018, 'iphone xs': 2018, 'iphone xs max': 2018,
        'iphone 11': 2019, 'iphone 11 pro': 2019, 'iphone 11 pro max': 2019,
        'iphone 12 mini': 2020, 'iphone 12': 2020, 'iphone 12 pro': 2020, 'iphone 12 pro max': 2020,
        'iphone 13 mini': 2021, 'iphone 13': 2021, 'iphone 13 pro': 2021, 'iphone 13 pro max': 2021,
        'iphone 14': 2022, 'iphone 14 plus': 2022, 'iphone 14 pro': 2022, 'iphone 14 pro max': 2022,
        'iphone 15': 2023, 'iphone 15 plus': 2023, 'iphone 15 pro': 2023, 'iphone 15 pro max': 2023,
        'iphone 16': 2024, 'iphone 16 plus': 2024, 'iphone 16 pro': 2024, 'iphone 16 pro max': 2024,
        'iphone 16e': 2025, 'iphone 17': 2025, 'iphone 17 pro': 2025, 'iphone 17 pro max': 2025, 'iphone 17e': 2026,"iphone air":2026
    }
    

def regex_float(s:str,default_value:int=0)->float:
    """Extracts the first float number found in a string."""
    if not s:
        return default_value
    s_clean = re.sub(r"[\s\xa0]", "", s)
    match = re.search(r"\d+[,.]?\d*", s_clean)
    if match:
        return float(match.group().replace(",", "."))
    return default_value
            

def regex(s:str,pattern:str,default_value:str="")->str:
    """Applies a regex pattern and returns the first match."""
    if not s:
        return default_value
    match = re.search(pattern,s)

    return match.group() if match else default_value


def normalize(s:str)->str:
    """Cleans text: lowercase, removes accents and extra spaces."""
    if not s:
        return ""
    # convert to lower case
    text = s.lower()

    text = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")
    # removing tab and line break   
    text = re.sub(r'[\n\r\t]', ' ', text)
    # deleting non usefull spaces 
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def storage_to_float(text:str)->float:
    """Converts a string containing 'go' or 'to' to a float (in GB)."""
    res = None
    if "to" in text:
        res = regex_float(text)*1000
    elif "go" in text:
        res = regex_float(text)
    return res

def extract_date(s:str):
    """Extracts and formats the sale date from eBay text (YYYY-MM-DD)."""
    if not s:
        return ""
    s = s.strip()
    match = re.search(r"(\d{1,2}|1er)\s+([a-zéû\.]+)(?:\s+(\d{4}))?", s)

    if not match:
        return ""
    
    day_str = match.group(1)
    month_str = match.group(2).replace(".", "") 
    year_extracted = match.group(3)
    

    day = "01" if day_str == "1er" else day_str.zfill(2)
    dict_months = {
        'janv': '01', 'janvier': '01','févr': '02', 'fevr': '02', 'février': '02','mars': '03',
        'avr': '04', 'avril': '04','mai': '05','juin': '06','juil': '07', 'juillet': '07',
        'août': '08', 'aout': '08','sept': '09', 'septembre': '09','oct': '10', 'octobre': '10',
        'nov': '11', 'novembre': '11','déc': '12', 'dec': '12', 'décembre': '12'
    }
    month = dict_months.get(month_str, "01")
    if year_extracted:
        year = year_extracted 
    else:
        actual_date = datetime.now()
        actual_year = actual_date.year
        actual_month = actual_date.month
        if int(month) > actual_month:
            year = str(actual_year - 1)
        else:
            year = str(actual_year)
    return f"{year}-{month}-{day}"

def get_phone_age(model: str) -> float:
    """Calculates the age of a phone model based on the current year"""
    if not model:
        return 2.0  
    
    current_year = datetime.now().year
    
    year = PHONE_CREATION_YEAR.get(model, current_year - 2)
    
    return float(current_year-year)


def filter_bad_price(price:float,lowest:int=30,highest:int=2500):
    """Returns True if the price is outside the expected range for a phone"""
    return price<lowest or price>highest


def is_accessory(title:str,price:float)->bool:
    """Returns True if the listing appears to be an accessory"""
    if not title:
        return True
    if price >= 150:
        return False
    
    return bool(regex(normalize(title),ACCESSORY_WORDS,False))


def title_starts_with_iphone(title:str):
    """Verifies that the title starts with iPhone"""
    if not title:
        return False
    title_norm = normalize(title).strip()
    return bool(re.match(r'^(apple\s+)?[^a-z]{0,10}iphone', title_norm))

def multi_variations_ad(title: str) -> bool:
    """returns True if the listing offers a choice between multiple models"""
    multi = r'(/.*?/|modeles\b|\bchoix\b)'
    return bool(regex(normalize(title),multi,False))

def is_locked_or_parts(description):
    """return true if the phone is locked or is not a phone"""
    if not description:
        return False
    
    
    return bool(regex(normalize(description),FORBIDDEN_WORDS,False))

def get_iphone_model(title:str):
    """Extracts and normalizes the exact iPhone model from the title."""
    if not title :
        return ""
    
    if regex(title, r"iphone\s*(\d{1,2}\s*)?air"):
        return "iphone air"
    
    model = regex(title, r"iphone\s*(\d{1,2}(?:\s*e(?![a-z]))?|xs\s*max|xs|xr|x|se)(\s*(pro(\s*max)?|plus|mini))?")
    if model:
        model = re.sub(r"(\d+)\s*e\b", r"\1e", model)
        model = re.sub(r"iphonex\b", "iphone x", model)
        model = re.sub(r"(\d+|xs|xr|se)",r" \1",model)
        model = re.sub(r"(\d+)(pro|plus|mini)", r"\1 \2", model)
        model = re.sub(r"(pro|xs)(max)", r"\1 \2", model) 
        model = re.sub(r"\s+", " ", model).strip()
        return model
    return ""


def face_id_not_working(desc):
    """Returns 1 if Face ID is mentioned as broken, 0 otherwise."""
    if re.search(r'face\s*id\s*(hs|out|marche pas|ne fonctionne|désactivé)', desc) or \
       re.search(r'(sans|problème|souci de)\s*face\s*id', desc):
        return 1 
    return 0 


def is_invalid_phone(current_ad:dict):
    """
    Returns True if the ad should be rejected
    """
    return (not title_starts_with_iphone(current_ad['Title']) or 
            not get_iphone_model(current_ad["Title"]) or
            is_locked_or_parts(current_ad["DescriptionStateBrut"]) or 
            is_accessory(current_ad['Title'], current_ad["PhonePrice"]) or 
            filter_bad_price(current_ad["PhonePrice"]) or 
            multi_variations_ad(current_ad["Title"]))

def block_css_and_image(route):
    """Intercepts and blocks images/CSS """
    if route.request.resource_type in ['image',"stylesheet","font","media"]:
        route.abort()
    else:
        route.continue_()

def random_moves(page)->None:
    for _ in range(rd.randint(1, 4)):

        page.mouse.move(rd.randint(0,1000),rd.randint(0,800),steps=120)
        

        time.sleep(rd.uniform(0.2, 1))
        for i in range(rd.randint(0,100)):
            page.mouse.wheel(0,rd.randint(20,100))
            time.sleep(0.05)

        time.sleep(rd.uniform(1, 2))

def selector_text(page,selector:str,multiple=False)->str:
    """Extracts raw text from a web element using a CSS selector """
    text = ""
    item = page.locator(selector)
    if item.count()>0:
        if not multiple:
            text = item.text_content()
        else:
            text = item.evaluate_all("list => list.reduce((prev,elt)=>prev+elt.textContent,'')")
    return text.lower()

def click_button(page,selector)->bool:
    """clicks an element if it exists"""
    button = page.locator(selector)
    if button.count()>0:
        button.click(timeout=4000)
        page.wait_for_timeout(1500) 
        return True
    return False

def multiple_selector_text(page,selector_list:list[str],multiple:bool=False):
    """Attempts to extract text from a list of fallback selectors"""
    for selector in selector_list:
        try:
            text = selector_text(page,selector,multiple)
            if text:
                return text
        except Exception as e:
            print(f"Error on this page :{page.url} this selector {selector} : {e}")
            continue
    return ""

def bypass_ebay_popups(page):
    """Closes eBay modals and clicks necessary buttons to reveal the actual ad"""
    page.wait_for_timeout(3000)
    click_button(page, '.x-prp-status-message a.ux-action') 
    click_button(page, ".x-item-condensed-card__message button")

def get_description(page) :
    """Extracts the seller description, bypassing iFrames if necessary"""
    frame_descr = page.frame_locator('iframe#desc_ifr')
    description = normalize(selector_text(frame_descr,".x-item-description-child",multiple=True)) 
    if not description:
        description = normalize(selector_text(page,'.ux-layout-section__textual-display--shortDescription'))
        if click_button(page,'.x-item-description button'):
            description = normalize(description+" "+selector_text(page.frame_locator('.ux-iframe iframe'),"body",multiple=True))
    return description

def extract_prices(page) -> tuple[float, float, float]:
    """Extracts and calculates prices (phone, shipping, total)"""
    phone_price = regex_float(multiple_selector_text(page, [".x-price-primary", ".x-bin-price__content"]))
    ship_price = regex_float(selector_text(page, '.ux-labels-values--shipping'))
    return phone_price, ship_price, phone_price + ship_price

def extract_vendor_info(page) -> tuple[str, float]:
    """Extracts vendor profile type (pro/individual) and satisfaction score"""
    vendor_raw = multiple_selector_text(page, ['.x-sellercard-atf__about-seller-item .ux-textspans--SECONDARY', ".x-prp-product-details_content"], multiple=True)
    vendor = regex(vendor_raw, r'pro|particulier')
    feedback = regex_float(selector_text(page, '.x-sellercard-atf__data-item button .ux-textspans--PSEUDOLINK'), None)
    return vendor if vendor else "particulier", feedback


def id_links_to_text(filename:str,ids:set)->None:
    with open(filename, "a") as f:
        for item_id in ids:
            f.write(item_id + "\n")


def txt_to_id_links(filename:str)->set:
    if not os.path.exists(filename):
        return set()
    with open(filename,"r") as f:
        return set(f.read().splitlines())

def get_links(page, nb_page:int,sold:bool=True,query:str="iphone")->set[str]:
    """Retrieves all listing links from an eBay results page"""
    if sold:
        url = f"{EBAY_LINK}sch/i.html?_nkw={query}&LH_Sold=1&LH_BIN=1&_pgn={nb_page}&_udlo=35&_sop=13"
    else:
        url = f"{EBAY_LINK}sch/i.html?_nkw={query}&LH_BIN=1&_pgn={nb_page}&_sop=10&_udlo=80"
    page.goto(url,wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    random_moves(page)
    hrefs = page.locator(
    ".srp-results .su-card-container__header a.s-card__link",#".brwrvr__item-results a.bsig__title__wrapper"
    ).evaluate_all(
        "els => els.map(el => el.href)")
    return set(hrefs)



def go_to_ebay(page, url: str, sold: bool = True) -> dict:
    """ 
    Take out the content from a html tag with a selector in parameter 
    return a string that contains the text of this html tag
    
    :param page the current page
    :param str selector the css selector
    :param boolean if true then it will take every items of this selector
    and return a string with a text of all items content
    :return the selected item's text content
    
"""
    page.goto(url, wait_until="domcontentloaded")
    bypass_ebay_popups(page)
    
    if sold and regex(selector_text(page, '.vim.x-bin-action'), "Achat immédiat"):
        raise ValueError('Redirection eBay vers autre page non vendu')

    title = selector_text(page, "h1")
    carac = multiple_selector_text(page, [".ux-layout-section--features", ".x-prp-product-details_content"])
    state_descr_brut = f"{title} {get_description(page)}"
    
    
    phone_price, ship_price, total_price = extract_prices(page)
    vendor, vendor_feedback = extract_vendor_info(page)
    model = get_iphone_model(state_descr_brut) 

    return {
        "Title": title,
        "Model": model,
        "Storage": storage_to_float(regex(f"{carac} {state_descr_brut}", r"[0-9]+\s*(go|to)")),
        "VendorFeedBacks": vendor_feedback,
        "Vendor": vendor,
        "EbayState": regex(f"{selector_text(page, '.x-item-condition-text')} {carac}", r"neuf|occasion|ouvert|reconditionné|pièces") or "occasion",
        "DescriptionStateBrut": state_descr_brut,
        "Battery": regex_float(regex(state_descr_brut, r"\d+%"), None),
        "FaceId": face_id_not_working(state_descr_brut),
        "PhonePrice": phone_price,
        "ShipPrice": ship_price,
        "TotalPrice": total_price,
        "Link": url,
        "Date": extract_date(selector_text(page, ".d-top-panel-message")) if sold else datetime.now().strftime("%Y-%m-%d"),
        "Age": get_phone_age(model)
    }

def check_every_links(page,links,sold):
    """Iterates over a set of links, extracts data, validates it and returns a list of dicts"""
    listings = []
    
    for link in links:
        try:    
            current_ad=go_to_ebay(page,link,sold)
                

            if (is_invalid_phone(current_ad=current_ad)):
                
                continue
            
            current_ad.pop("Title",None)
            current_ad["Link"] = link
            listings.append(current_ad)
        except Exception as e:
                        print(f"Error on this link {link} : {e}")
                        continue
    return listings


def links_to_content(links:set,sold:bool=True)->pd.DataFrame:
    """Main entry point,
      Launches Playwright, 
      manages context and returns a clean DataFrame"""
    if not links:
        print("Aucun nouveau lien à scraper.")
        return pd.DataFrame()
    with sync_playwright() as p :
        browser = p.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 768},
        locale="fr-FR"
        )
        page = context.new_page()
        page.goto(EBAY_LINK)

        click_button(page,'button:has-text("Accepter")')

        listings = check_every_links(page=page,links=links,sold=sold)

        new_df = pd.DataFrame(listings)  
        browser.close()
        return new_df



"""scrap the content of listing ebay, and return a data frame that contains links of every listings

"""
def scrap_listing(filename_history:str,sold:bool=True,query:str="iphone",nb_max_pages:int=1)->set:
    data = set()
    nb_page = 1
    history_links = txt_to_id_links(filename_history)

    with sync_playwright() as p:
        browser = p.chromium.launch(    
        headless=True,
        args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 768},
        locale="fr-FR"
        )
        page = context.new_page()
        page.route("**/*", block_css_and_image)
        page.goto(f"{EBAY_LINK}/sch/i.html?_nkw={query}&LH_BIN=1&_pgn=1&_sop=13")# &_ipg=240 to get 240 ads per page
        
        while nb_page<=nb_max_pages:
            hrefs = get_links(page,nb_page,sold,query)
            if len(hrefs)<3:
                break
            current_ids = {regex(href, r"itm/\d+") for href in hrefs if regex(href, r"itm/\d+")}
            new_ids = current_ids-history_links
            if len(new_ids)==0:
                break
            history_links.update(new_ids)
            time.sleep(rd.uniform(1.5, 4.0))
            clean_links = {f"{EBAY_LINK}{item_id}" for item_id in new_ids}
           
            data.update(clean_links)
            id_links_to_text(filename_history, new_ids)
            nb_page+=1

        
        
        browser.close()

    return data

