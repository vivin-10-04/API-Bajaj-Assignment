from trading_sdk import TradingClient

client = TradingClient()
file_name = "output.txt"

try:
    with open(file_name, "w") as file:
        file.write("--- Instruments ---\n")

        instruments = client.get_instruments()
        file.write(str(instruments) + "\n")

        file.write("--- Placing BUY Order (AAPL) ---\n")
        order = client.place_order("AAPL", 10, "BUY", "MARKET")
        file.write("Order Response: " + str(order) + "\n")

        file.write("--- Portfolio ---\n")
        pf = client.get_portfolio()
        file.write(str(pf) + "\n")

        file.write("--- Placing SELL Order (AAPL) ---\n")
        client.place_order("AAPL", 5, "SELL", "MARKET")

        file.write("--- Final Portfolio ---\n")
        final_pf = client.get_portfolio()
        file.write(str(final_pf) + "\n")

except Exception as e:
    print("error found:", e)
