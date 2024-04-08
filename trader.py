from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string
import numpy as np

class Trader:
    def __init__(self) -> None:
        # Risk factor for each product, pre-set
        self.gamma = {
            "AMETHYSTS" : 10,
            "STARFRUIT" : 10,
            "PRODUCT1"  : 10,
            "PRODUCT2"  : 10,
        }

        # Used to store the past trade price ratio to the previous timestamp => calculate Market volatility
        self.past_trade_ratio = []

        # The initial trade price
        # TODO: What should we set
        self.last_avg_trade_price = {
            "AMETHYSTS" : 1,
            "STARFRUIT" : 1,
            "PRODUCT1"  : 1,
            "PRODUCT2"  : 1,
        }

        # TODO: What is this?
        self.max_timestamp = 1000000

        # Initial last timestamp
        self.last_timestamp = 0

        # Position Limit for each product
        self.position_limit = {
            "AMETHYSTS" : 20,
            "STARFRUIT" : 20,
            "PRODUCT1"  : 20,
            "PRODUCT2"  : 20,
        }

    # Get the mid price for the orderbook
    def mid_price(self, order_book: OrderDepth):
        max_bid = None
        min_ask = None

        for bid_price in order_book.buy_orders:
            max_bid = bid_price if max_bid is None else max(max_bid, bid_price)
        
        for ask_price in order_book.sell_orders:
            min_ask = ask_price if min_ask is None else min(min_ask, ask_price)

        if max_bid is None:
            return min_ask
        
        if min_ask is None:
            return max_bid
        
        return (min_ask + max_bid) / 2
    
    # Get AVG trade price
    def avg_trade_price(self, market_trade):
        total_price = 0
        total_count = 0

        for trade in market_trade:
            total_price += trade.price
            total_count += trade.quantity

        if total_count == 0:
            return 0
        
        return total_price / total_count
    
    # Get total market volumn
    def total_volumn(self, order_book: OrderDepth):
        vol = 0

        for bid_price in order_book.buy_orders:
            vol += order_book.buy_orders[bid_price]
        
        for ask_price in order_book.sell_orders:
            vol -= order_book.sell_orders[ask_price]

        return vol

    # Calculate all AS parameters and return a hashmap for it
    def calc_AS_params(self, product_name, trading_state: TradingState):
        params = {}

        # Current market mid-price(s)
        order_book = trading_state.order_depths[product_name]
        params["s"] = self.mid_price(order_book)

        # Market volatility(σ)
        trade_data = trading_state.market_trades[product_name]
        cur_avg_trade_price = self.avg_trade_price(trade_data)
        R_cur = cur_avg_trade_price / self.last_avg_trade_price[product_name]
        self.past_trade_ratio.append(R_cur)

        params["sigma"] = np.std(self.past_trade_ratio)
        self.last_avg_trade_price[product_name] = cur_avg_trade_price

        # Normalized closing time(T)
        params["T"] = 1

        # Current time as a fraction of T (t)
        params["t"] = trading_state.timestamp / self.max_timestamp

        # Risk Factor (γ)
        params["gamma"] = self.gamma[product_name]

        # Order Book Depth (κ)
        time_diff = trading_state.timestamp - self.last_timestamp
        if time_diff == 0:
            time_diff += 1 # TODO: What should we do?
        params["kappa"] = self.total_volumn(order_book) / time_diff

        # Inventory quantity of base asset(positive/negative for long/short position) (q)
        params["q"] = trading_state.position[product_name]

        # Update macros
        self.last_timestamp = trading_state.timestamp

        return params
    
    def deploy_AS(self, AS_params, product_name, trading_state: TradingState):
        trades = []

        # Extract parameters
        s = AS_params["s"]
        sigma = AS_params["sigma"]
        T = AS_params["T"]
        t = AS_params["t"]
        gamma = AS_params["gamma"]
        kappa = AS_params["kappa"]
        q = AS_params["q"]

        # Reservation Price
        r = s - q * gamma * sigma * sigma # * (T - t) # Not used for now

        # Optimal bid/ask spread
        delta = (gamma * sigma * sigma + 2 * np.log(1 + gamma / kappa) / gamma) / 2 # * (T - t) # Not used for now

        # Trade Price
        bid_price = r - delta
        ask_price = r + delta

        # Trade Volumn
        bid_volume = self.position_limit[product_name] - trading_state.position[product_name]
        ask_volume = trading_state.position[product_name] + self.position_limit[product_name]

        trades.append(Order(product_name, bid_price, bid_volume))
        trades.append(Order(product_name, ask_price, -ask_volume))
        return trades
    
    def run(self, state: TradingState):
        # print("traderData: " + state.traderData)
        # print("Observations: " + str(state.observations))
        result = {}

        for product in state.order_depths:
            product_params = self.calc_AS_params(product, state)

            trades = self.deploy_AS(product_params, product, state)

            result[product] = trades  
    
        traderData = "HAHA" # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.
        
        conversions = 1
        return result, conversions, traderData