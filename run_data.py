from trader import Trader
from datamodel import Listing, OrderDepth, Trade, TradingState

data_folder = "round-1-island-data-bottle"

# market_files = ["prices_round_1_day_-2.csv", "prices_round_1_day_-1.csv", "prices_round_1_day_0.csv"]
# trade_files = ["trades_round_1_day_-2_nn.csv", "trades_round_1_day_-1_nn.csv", "trades_round_1_day_0_nn.csv"]
market_files = ["prices_round_1_day_0.csv"]
trade_files = ["trades_round_1_day_0_nn.csv"]

import csv
import matplotlib.pyplot as plt

def print_state(state: TradingState):
        print("----- STATE -----")
        print("Time:", state.timestamp)
        print("Books:")
        for product in state.order_depths:
            print(" Product:", product)
            print("     BUY:")
            for buy_price in state.order_depths[product].buy_orders:
                print("         price -- volume:", buy_price, state.order_depths[product].buy_orders[buy_price])
            print("     SELL:")
            for sell_price in state.order_depths[product].sell_orders:
                print("         price -- volume:", sell_price, state.order_depths[product].sell_orders[sell_price])

        print("Trades:")
        for p in state.market_trades:
            print(" Product:", p)
            tList = state.market_trades[p]
            print("     Trade:")
            for t in tList:
                print("         price -- volume:", t.price, t.quantity)

        print("Position:")
        for product in state.position:
            print(" Product --  position:", product, state.position[product])
        
        print("\n")

# Get the mid price for the orderbook
def mid_price(order_book: OrderDepth):
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

if __name__ == "__main__":
    market_data = []
    trade_data = []
    trading_states = []

    timestamp_base = 0

    # Retrieve data from files
    for market_file in market_files:
        path = data_folder + "/" + market_file

        with open(path, 'r') as file:
            # Create a CSV reader object
            csv_reader = csv.reader(file)
            
            first_row = True
            # Iterate over each row in the CSV file
            for row in csv_reader:
                # Skip label row
                if first_row:
                    first_row = False
                    continue
                
                data = row[0].split(";")

                # Extract data
                timestamp = int(data[1]) + timestamp_base
                product = data[2]
                
                bid_book = {}
                for i in [3,5,7]:
                    if data[i] != "":
                        bid_book[float(data[i])] = int(data[i+1])

                ask_book = {}
                for i in [9,11,13]:
                    if data[i] != "":
                        ask_book[float(data[i])] = -int(data[i+1])

                order_depth = OrderDepth(bid_book, ask_book)

                last_timestamp = -100 if len(market_data) == 0 else market_data[-1][0]
                
                if timestamp == last_timestamp:
                    market_data[-1][1][product] = order_depth
                else:
                    market_data.append((timestamp, {product : order_depth}))

                # if len(market_data) < 10:
                #     print("------")
                #     print("Time:", market_data[-1][0])
                #     for p in market_data[-1][1]:
                #         print("Product:", p)
                #         od = market_data[-1][1][p]
                #         print("     Buy orders:")
                #         for price in od.buy_orders:
                #             print(price, "--", od.buy_orders[price])
                #         print("     Sell orders:")
                #         for price in od.sell_orders:
                #             print(price, "--", od.sell_orders[price])
                #     print("------")
        
        timestamp_base = market_data[-1][0]

    timestamp_base = 0
    for trade_file in trade_files:
        path = data_folder + "/" + trade_file

        with open(path, 'r') as file:
            # Create a CSV reader object
            csv_reader = csv.reader(file)
            
            first_row = True
            # Iterate over each row in the CSV file
            for row in csv_reader:
                # Skip label row
                if first_row:
                    first_row = False
                    continue
                
                data = row[0].split(";")

                # Extract data
                timestamp = int(data[0]) + timestamp_base
                product = data[3]
                price = float(data[5])
                quantity = int(data[6])

                last_timestamp = -100 if len(trade_data) == 0 else trade_data[-1][0]
                
                if timestamp != last_timestamp:
                    trade_data.append((timestamp, {product : []}))

                if product not in trade_data[-1][1]:
                    trade_data[-1][1][product] = []
                
                trade_data[-1][1][product].append(Trade(product, price, quantity))

                # if len(trade_data) < 10:
                #     print("------")
                #     print("Time:", trade_data[-1][0])
                #     for p in trade_data[-1][1]:
                #         print("Product:", p)
                #         tList = trade_data[-1][1][p]
                #         print("     Trade:")
                #         for t in tList:
                #             print(t.price, "--", t.quantity)
                #     print("------")
        timestamp_base = trade_data[-1][0]
    
    # Create trading states
    trade_data_index = 0
    for cur_market_data in market_data:
        timestamp = int(cur_market_data[0])

        if trade_data_index >= len(trade_data) or timestamp != trade_data[trade_data_index][0]:
            trading_state = TradingState("", timestamp, {}, cur_market_data[1], {}, {}, {}, None)
        else:
            trading_state = TradingState("", timestamp, {}, cur_market_data[1], {}, trade_data[trade_data_index][1], {}, None)
            trade_data_index += 1
        
        trading_states.append(trading_state)
    
    # # Check Trading state
    # for ts in trading_states[:10]:
    #     print_state(ts)

    # Run our trade and do order matching
    position = {}
    money = 0
    assets = []

    trader = Trader()
    for state in trading_states:
        # print("Time:", state.timestamp)

        # Update to the correct position
        state.position = position

        # Run the trader algo
        orders, _, _ = trader.run(state)

        # Order matching
        for product in orders:
            # Check if there is market has this product now
            if product not in state.order_depths:
                continue

            for my_trade in orders[product]:
                price = my_trade.price
                quantity = my_trade.quantity

                # We want to buy (placed a bid)
                if quantity > 0:
                    # Match a sell order (ask)
                    asks = sorted(state.order_depths[product].sell_orders.items())

                    for ask in asks:
                        ask_price = ask[0]
                        ask_volume = ask[1]

                        # Order Executed
                        if ask_price <= price:
                            executed_quantity = min(quantity, ask_volume)
                            quantity -= executed_quantity

                            if product not in position:
                                position[product] = 0

                            position[product] += executed_quantity
                            money -= executed_quantity * ask_price
                else: # We want to sell (placed a sell)
                    quantity = -quantity
                    # Match a buy order (bid)
                    bids = sorted(state.order_depths[product].buy_orders.items(), reverse=True)

                    for bid in bids:
                        bid_price = bid[0]
                        bid_volume = bid[1]

                        # Order Executed
                        if bid_price >= price:
                            executed_quantity = min(quantity, bid_volume)
                            quantity -= executed_quantity

                            if product not in position:
                                position[product] = 0

                            position[product] -= executed_quantity
                            money += executed_quantity * bid_price
        
        asset = money
        # Calculate total asset from mid price
        for product in position:
            volume = position[product]

            product_price = mid_price(state.order_depths[product])
            asset += volume * product_price

        assets.append(asset)
        # print("Asset:", asset)
    
    plt.plot(assets)

    # Add labels and title
    plt.xlabel('Time')
    plt.ylabel('Total Asset')
    plt.title('Plot of List of Numbers')

    # Display the plot
    plt.show()



            