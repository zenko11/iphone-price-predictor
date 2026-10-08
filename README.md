# iphone-price-predictor
AI-powered eBay bot using XGBoost and NLP to predict iPhone market prices and alert on undervalued listings in real-time

## Overview

This project monitors iPhone listings on eBay France and estimates whether a listing could represent a profitable opportunity.

The application:

- Scrapes active iPhone listings from eBay
- Extracts the model, storage capacity, condition, battery health and price
- Filters out accessories, spare parts and invalid listings
- Uses NLP to classify the physical condition of the phone
- Predicts the estimated resale price with an XGBoost model
- Calculates the potential profit and prediction risk
- Sends profitable opportunities to Discord

## How it works

The main pipeline is:

1. Search for iPhone listings on eBay
2. Extract and clean listing data
3. Detect the iPhone model and technical characteristics
4. Classify the phone's condition using regex rules and zero-shot NLP
5. Predict its estimated market price
6. Calculate the potential profit
7. Send an alert to Discord if the opportunity reaches the configured threshold

## Requirements

- Python 3.10 or newer
- Chromium
- An eBay account may be required depending on eBay's access rules
- A Discord webhook URL for notifications

## Installation

Clone the repository:

```bash
git clone https://github.com/zenko11/iphone-price-predictor.git
cd iphone-price-predictor
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```
On macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Install the Chromium browser used by Playwright:

```bash
playwright install chromium
```
## Configuration

Create a `.env` file in the root directory:

```env
URL_DISCORD=https://discord.com/api/webhooks/your-webhook-url
```
The webhook is used to send detected opportunities to a Discord channel.

Do not commit your `.env` file or expose your webhook URL publicly.
## Run the bot

```bash
python main.py
```
The application searches for listings, analyzes them and sends Discord notifications when the estimated potential profit is greater than the configured threshold.

## Configuration parameters

The main settings can be adjusted in `main.py`:

- `NB_MAX_PAGE_TO_SEE`: maximum number of eBay pages to scan
- `MIN_NET_PROFIT`: minimum potential profit required for a notification
- `EBAY_FEE_RATE`: estimated eBay selling fee
- `SHIPPING_COST`: estimated shipping cost
- `SEARCH_QUERIES`: list of search queries used on eBay

## Machine learning

The project uses:

- XGBoost for price prediction
- A saved preprocessing pipeline for feature transformation
- A zero-shot DeBERTa model for classifying phone condition
- A risk table based on historical prediction errors

The price prediction uses features such as:

- iPhone model
- Storage capacity
- Seller type
- Seller feedback
- Battery health
- Face ID status
- Phone age
- Physical condition

## Important limitations

- eBay selectors and page structure may change over time
- Scraping availability depends on eBay access rules and network conditions
- Predictions are estimates and should not be considered guaranteed resale prices
- The risk level depends on the amount and quality of historical training data
- Discord notifications require a valid webhook URL
- The NLP model can require significant memory and may take time to load

## Disclaimer

The project does not guarantee profit or prediction accuracy.
