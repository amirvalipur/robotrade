import MetaTrader5 as mt
from pprint import pprint
from datetime import datetime
import yfinance as yf
import time


# _______________________________________________________________________________________________    start
class Martingale:
    def __init__(self, symbol='EURUSD', lot=0.01, comment='', deviation=20):
        # connect to metatrader & set basic data
        self.start = mt.initialize(
            login='*******',
            password="*******",
            server="***********",
            portable=False,
        )
        if not self.start:
            print('initialize fail --> quit')
            quit()
        print("START")
        self.position_id = None
        self.symbol = symbol
        self.lot = lot
        self.comment = comment
        self.deviation = deviation
        self.point = mt.symbol_info(symbol).point
        self.price = mt.symbol_info_tick(symbol).ask
        self.ask_price = 0
        self.bid_price = 0
        self.result = None
        self.stops = True

    def symbol_check(self):
        # make sure found target symbol
        symbol_info = mt.symbol_info(self.symbol)
        if not symbol_info:
            print('symbol not found --> quit')
            mt.shutdown()
            quit()

        if not symbol_info.visible:
            print(self.symbol, "is not visible, trying to switch on")
            if not mt.symbol_select(self.symbol, True):
                print("symbol_select({}}) failed --> quit", self.symbol)
                mt.shutdown()
                quit()
        print('symbol_check  -->  OK')

    def get_current_price(self):
        tick = mt.symbol_info_tick(self.symbol)
        if tick is not None:
            return tick.bid, tick.ask
        else:
            print(f"Failed to retrieve tick data for {self.symbol}.")
            return None, None

    def calculate_current_profit(self):
        positions = mt.positions_get(symbol=self.symbol)
        total_profit = 0.0

        if positions is not None and len(positions) > 0:
            for position in positions:
                if position.symbol == self.symbol:
                    if position.type == mt.ORDER_TYPE_BUY:
                        # For a Buy position, calculate profit using the current bid price
                        current_price = mt.symbol_info_tick(self.symbol).bid
                        profit = (current_price - position.price_open) * position.volume
                    elif position.type == mt.ORDER_TYPE_SELL:
                        # For a Sell position, calculate profit using the current ask price
                        current_price = mt.symbol_info_tick(self.symbol).ask
                        profit = (position.price_open - current_price) * position.volume
                    else:
                        print(f"Unknown position type: {position.type}")
                        continue

                    total_profit += profit

        return total_profit

    def send_order_buy(self):
        request = {
            "action": mt.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": self.lot,
            "type": mt.ORDER_TYPE_BUY,
            "price": self.price,
            "deviation": self.deviation,
            "magic": 234000,
            "comment": self.comment,
            "type_time": mt.ORDER_TIME_GTC,
            "type_filling": 0
        }
        self.result = mt.order_send(request)
        self.stops = False
        self.position_id = self.result.order

        if self.result.retcode != mt.TRADE_RETCODE_DONE:
            print("2.send order : failed, retcode={}".format(self.result.retcode))
            result_dict = self.result._asdict()
            pprint(result_dict)
            print("shutdown() --> quit")
            mt.shutdown()
            quit()

        print("send buy order --> success")
        result_dict = self.result._asdict()
        self.ask_price = result_dict['ask']
        result_x = {}
        report_list = ['ask', 'bid', 'order', 'volume']
        for key, value in result_dict.items():
            if key in report_list:
                result_x.update({key: value})
        print(result_x)

    def send_order_sell(self):
        request = {
            "action": mt.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": self.lot,
            "type": mt.ORDER_TYPE_SELL,
            "price": self.price,
            "deviation": self.deviation,
            "magic": 234000,
            "comment": self.comment,
            "type_time": mt.ORDER_TIME_GTC,
            "type_filling": 0
        }
        self.result = mt.order_send(request)
        self.stops = False
        self.position_id = self.result.order

        if self.result.retcode != mt.TRADE_RETCODE_DONE:
            print("2.send order : failed, retcode={}".format(self.result.retcode))
            result_dict = self.result._asdict()
            pprint(result_dict)
            print("shutdown() --> quit")
            mt.shutdown()
            quit()

        print("send sell order --> success")
        result_dict = self.result._asdict()
        self.bid_price = result_dict['bid']
        result_x = {}
        report_list = ['ask', 'bid', 'order', 'volume']
        for key, value in result_dict.items():
            if key in report_list:
                result_x.update({key: value})
        print(result_x)

    #     _______________________________________________________________
    def stops_dynamic_buy(self):
        # set sto ploss during the transaction
        dynamic_sell, dynamic_buy = self.get_current_price()
        request = {
            'action': mt.TRADE_ACTION_SLTP,
            "position": self.position_id,
            'symbol': self.symbol,
            'sl': dynamic_sell - 100 * self.point,
            "magic": 234000,
        }
        self.result = mt.order_send(request)
        if self.result.retcode == mt.TRADE_RETCODE_DONE:
            self.stops = True

    def stops_dynamic_sell(self):
        # set stop loss during the transaction
        dynamic_sell, dynamic_buy = self.get_current_price()
        request = {
            'action': mt.TRADE_ACTION_SLTP,
            "position": self.position_id,
            'symbol': self.symbol,
            'sl': dynamic_buy + 100 * self.point,
            "magic": 234000,
        }
        self.result = mt.order_send(request)
        if self.result.retcode == mt.TRADE_RETCODE_DONE:
            self.stops = True

    #     _______________________________________________________________

    def stops_change_buy(self):
        # set initial stop loss & take profit
        request = {
            'action': mt.TRADE_ACTION_SLTP,
            "position": self.position_id,
            'symbol': self.symbol,
            'sl': self.ask_price - 100 * self.point,
            'tp': self.ask_price + 200 * self.point,
            "magic": 234000,
        }
        self.result = mt.order_send(request)
        if self.result.retcode == mt.TRADE_RETCODE_DONE:
            self.stops = True

    def stops_change_sell(self):
        # set initial stop loss & take profit
        request = {
            'action': mt.TRADE_ACTION_SLTP,
            "position": self.position_id,
            'symbol': self.symbol,
            'sl': self.bid_price + 100 * self.point,
            'tp': self.bid_price - 200 * self.point,
            "magic": 234000,
        }
        self.result = mt.order_send(request)
        if self.result.retcode == mt.TRADE_RETCODE_DONE:
            self.stops = True

    # ______________________________________________________________________________
    def close_order(self):
        request = {
            "action": mt.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": self.lot,
            "type": mt.ORDER_TYPE_SELL,
            "position": self.position_id,
            "price": self.price,
            "deviation": self.deviation,
            "magic": 234000,
            "comment": self.comment,
            "type_time": mt.ORDER_TIME_GTC,
            "type_filling": mt.ORDER_FILLING_RETURN,
        }
        self.result = mt.order_send(request)
        if self.result.retcode == mt.TRADE_RETCODE_DONE:
            print('close position manually')

    # Function to calculate EMA
    def fetch_data(self, ticker, period, interval):
        # fetch data from yahoo finance
        data = yf.download(ticker, period=period, interval=interval)
        return data

    def compute_moving_averages(self, data):
        data['MA_25'] = data['Close'].rolling(window=25).mean()
        data['MA_50'] = data['Close'].rolling(window=50).mean()
        return data

    def decide_order(self, data):
        last_row = data.iloc[-1]

        if last_row['MA_25'] > last_row['MA_50']:
            val_res = "Buy_Order"
            val_25 = last_row['MA_25']
            val_50 = last_row['MA_50']
            return val_res, val_25, val_50
        elif last_row['MA_25'] < last_row['MA_50']:
            val_res = "Sell_Order"
            val_25 = last_row['MA_25']
            val_50 = last_row['MA_50']
            return val_res, val_25, val_50
        else:
            val_res = "HOLD"
            val_25 = last_row['MA_25']
            val_50 = last_row['MA_50']
            return val_res, val_25, val_50


# _______________________________________________________________________________________________ EMA strategy
flag = True
start_time = datetime.now()
trend = None
position_number = 0
profit_number = 0
loss_number = 0
try_to_fix_sltp = 0
default = 0.01

mart = Martingale()

while True:
    try_to_download_data = 1
    last_profit = 1
    if flag:
        if position_number >= 10:
            print('transactions ended . . . !')
            break
        else:
            position_number += 1
            print('transaction --> ', position_number)
            # ____________________________________
            while True:
                try:
                    ticker = "EURUSD=X"
                    # ticker = "BTC-USD"
                    timeframe = '15m'
                    data = mart.fetch_data(ticker, period='5d', interval=timeframe)
                    data = data.dropna()

                    # 25 and 50 moving averages
                    data = mart.compute_moving_averages(data)

                    val_res, val_25, val_50 = mart.decide_order(data)

                    # ________________________________________________________________________
                    if val_res == 'Buy_Order':
                        trend = True
                        mart.send_order_buy()
                        print(f'ema 25 : {val_25} , ema 50 : {val_50}')
                        break
                    elif val_res == 'Sell_Order':
                        trend = False
                        mart.send_order_sell()
                        print(f'ema 25 : {val_25} , ema 50 : {val_50}')
                        break
                    elif val_res == 'HOLD':
                        print(f'ema 25 : {val_25} , ema 50 : {val_50}')
                        print('hold 15 min')
                        time.sleep(900)
                    else:
                        print('Delta_Flag calculate error')
                        flag = False
                        break
                except:
                    try_to_download_data += 1
                    time.sleep(10)

    else:
        break
    print(f'try for download data --> {try_to_download_data}')
    while True:
        number_of_posiation = mt.positions_total()
        if number_of_posiation == 0:
            if trend:
                ask = mart.ask_price
                bid = mt.symbol_info_tick(mart.symbol).bid
                profit = bid - ask
            else:
                bid = mart.bid_price
                ask = mt.symbol_info_tick(mart.symbol).ask
                profit = bid - ask
            if profit > 0:
                profit_number += 1
                print('profit --> ', profit_number)
                print('___________________________________________________________________')
                break
            elif profit < 0:
                loss_number += 1
                print('loss --> ', loss_number)
                print('___________________________________________________________________')
                break
            else:
                print('profit calculate error')
                print('___________________________________________________________________')
                flag = False
                break
        elif number_of_posiation > 0:
            if mart.stops:
                time.sleep(10)
                # ____________________________________
                current_profit = mart.calculate_current_profit()
                if current_profit > last_profit:
                    if trend:
                        mart.stops_dynamic_buy()
                        last_profit = current_profit
                    else:
                        mart.stops_dynamic_sell()
                        last_profit = current_profit
                # ____________________________________
                time.sleep(10)
            else:
                if trend:
                    mart.stops_change_buy()
                    try_to_fix_sltp += 1
                else:
                    mart.stops_change_sell()
                    try_to_fix_sltp += 1
                if mart.stops:
                    print(f'set sltp --> succes ({try_to_fix_sltp})')
                    try_to_fix_sltp = 0
                else:
                    time.sleep(5)

mt.shutdown()
end_time = datetime.now()
time_long = (end_time - start_time).seconds // 3600
pprint({'time': time_long, 'profit': profit_number, 'loss': loss_number})
print('4.END')
