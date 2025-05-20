# Tradebot-with-Hummingbot

## Overview
This final project aim to build a HFT bot which has AI model using hummingbot to trade crypto currencies on various broker such as Binance, Kucoin, Coinbase, .....

## Installation
Clone this repo and install with
```
pip install -r requirements.txt
``` 

## Re-run demo
First run this command : 
``` 
cd research_notebooks/bitcoinenaitor
``` 

Follow [this link]([https://example.com](https://hummingbot.org/installation/docker/)) to install Hummingbot via docker, then start hummingbot bot and run this script on current terminal : 
``` 
python prediction_service.py
``` 


On hummingbot terminal run this script : 
``` 
start --script ml_signal_listener.py --config ml_signal_listener_config.yml
``` 


## File description

There are couple of files that contain majority of our demo : <br> 
**0_download_candles.ipynb** : this notebook describe our data pulling progress for our AI model. <br>
**1_feature_engineering.ipynb** : this notebook describe how we process our data or add certain indicators. <br>
**2_modelling.ipynb** : this notebook describe how we train our AI model (xgboost, neural net, transformer,....) and its result. <br>
**prediction_service.py** : this code show how we use our trained model to predict newest data. <br>
**ml_signal_listener.py** : this code demonstrate how we send signal from prediction service to our hummingbot bot. <br>


