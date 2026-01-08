import requests

class TradingClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url

    def get_instruments(self):
        """Fetches list of tradable instruments."""
        resp = requests.get(f"{self.base_url}/api/v1/instruments")
        resp.raise_for_status()
        return resp.json()

    def place_order(self, symbol, quantity, side, order_type="MARKET", price=None):
        """
        Places a new order.
        side: 'BUY' or 'SELL'
        order_type: 'MARKET' or 'LIMIT'
        """
        payload = {
            "symbol": symbol,
            "quantity": quantity,
            "orderType": side,
            "orderStyle": order_type,
            "price": price
        }
        resp = requests.post(f"{self.base_url}/api/v1/orders", json=payload)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            print(f"Error: {resp.json()}")
            raise
        return resp.json()

    def get_order_status(self, order_id):
        resp = requests.get(f"{self.base_url}/api/v1/orders/{order_id}")
        resp.raise_for_status()
        return resp.json()

    def get_portfolio(self):
        resp = requests.get(f"{self.base_url}/api/v1/portfolio")
        resp.raise_for_status()
        return resp.json()