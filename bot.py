import os
import logging
from decimal import Decimal, InvalidOperation

from binance import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException


# ------------------- Logging Setup -------------------
LOG_FILE = "trading_bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ],
)

logger = logging.getLogger("BasicBot")


# ------------------- Core Bot Class -------------------
class BasicBot:
    """
    Simplified Binance USDT-M Futures Testnet trading bot.
    Supports: MARKET, LIMIT, STOP-LIMIT orders (BUY/SELL).
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        # Use python-binance client
        self.client = Client(api_key, api_secret, testnet=testnet)

        # Point futures to Testnet
        if testnet:
            # this is the standard futures testnet base
            self.client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

        logger.info("Client initialized (testnet=%s)", testnet)

    # ---------- Internal helper ----------
    def _safe_call(self, func, description: str, **params):
        """
        Wrap API calls with logging and error handling.
        """
        logger.info("API Request: %s | Params: %s", description, params)
        try:
            response = func(**params)
            logger.info("API Response (%s): %s", description, response)
            return response

        except BinanceAPIException as e:
            logger.error("Binance error during %s: %s", description, e, exc_info=True)

            # helpful message for common errors
            if e.code == -1022:
                print(
                    "[ERROR] Invalid signature (-1022).\n"
                    "Check that:\n"
                    "  * You are using TESTNET keys\n"
                    "  * You pasted API key/secret on a single line\n"
                    "  * System time is correct."
                )
            elif e.code == -4164:
                print(
                    "[ERROR] Order notional too small (-4164).\n"
                    "Increase quantity so that price * quantity >= 100 USDT\n"
                    "and ensure you have enough margin in Futures wallet."
                )
            else:
                print(f"[ERROR] Binance error during {description}: {e}")

        except BinanceRequestException as e:
            logger.error("Binance request error during %s: %s", description, e, exc_info=True)
            print(f"[ERROR] Network/HTTP error during {description}: {e}")

        except Exception as e:
            logger.error("Unexpected error during %s: %s", description, e, exc_info=True)
            print(f"[ERROR] Unexpected error during {description}: {e}")

        return None

    # ---------- Public methods ----------
    def place_market_order(self, symbol: str, side: str, quantity: float):
        """
        Place a MARKET order on USDT-M Futures.
        """
        side = side.upper()
        description = f"Futures MARKET {side} {symbol}"
        return self._safe_call(
            self.client.futures_create_order,
            description,
            symbol=symbol.upper(),
            side=side,
            type="MARKET",
            quantity=quantity,
        )

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC",
    ):
        """
        Place a LIMIT order on USDT-M Futures.
        """
        side = side.upper()
        description = f"Futures LIMIT {side} {symbol}"
        return self._safe_call(
            self.client.futures_create_order,
            description,
            symbol=symbol.upper(),
            side=side,
            type="LIMIT",
            timeInForce=time_in_force,
            quantity=quantity,
            price=price,
        )

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        limit_price: float,
        time_in_force: str = "GTC",
    ):
        """
        BONUS: Place a STOP-LIMIT order on USDT-M Futures.
        Futures API: type='STOP' with stopPrice + price.
        """
        side = side.upper()
        description = f"Futures STOP-LIMIT {side} {symbol}"
        return self._safe_call(
            self.client.futures_create_order,
            description,
            symbol=symbol.upper(),
            side=side,
            type="STOP",
            timeInForce=time_in_force,
            quantity=quantity,
            price=limit_price,
            stopPrice=stop_price,
        )

    def get_symbol_price(self, symbol: str):
        """
        Helper to fetch current mark price.
        """
        description = f"Get mark price for {symbol}"
        return self._safe_call(
            self.client.futures_mark_price,
            description,
            symbol=symbol.upper(),
        )


# ------------------- CLI Helpers -------------------
def _read_decimal(prompt: str, positive: bool = True) -> Decimal:
    while True:
        raw = input(prompt).strip()
        try:
            value = Decimal(raw)
            if positive and value <= 0:
                print("Value must be > 0.")
                continue
            return value
        except InvalidOperation:
            print("Invalid number, please try again.")


def _read_side() -> str:
    while True:
        side = input("Side (BUY/SELL): ").strip().upper()
        if side in ("BUY", "SELL"):
            return side
        print("Invalid side. Please enter BUY or SELL.")


def _read_symbol(default: str = "BTCUSDT") -> str:
    symbol = input(f"Symbol (default {default}): ").strip().upper()
    return symbol if symbol else default


def print_order_result(response):
    if not response:
        print("No response (order failed or was not sent).")
        return

    # Futures order typical fields
    order_id = response.get("orderId")
    status = response.get("status")
    client_order_id = response.get("clientOrderId")
    avg_price = response.get("avgPrice", "N/A")
    executed_qty = response.get("executedQty", "0")

    print("\n=== ORDER RESULT ===")
    print(f"Order ID       : {order_id}")
    print(f"Client Order ID: {client_order_id}")
    print(f"Status         : {status}")
    print(f"Avg Price      : {avg_price}")
    print(f"Executed Qty   : {executed_qty}")
    print("====================\n")


# ------------------- Main CLI -------------------
def main():
    print("=== Binance Futures Testnet Bot (USDT-M) ===")

    # Get API keys from env or prompt
    api_key = os.getenv("BINANCE_API_KEY") or input("Enter API Key: ").strip()
    api_secret = os.getenv("BINANCE_API_SECRET") or input("Enter API Secret: ").strip()

    bot = BasicBot(api_key, api_secret, testnet=True)

    while True:
        print("\n--- Menu ---")
        print("1) Place MARKET order")
        print("2) Place LIMIT order")
        print("3) Place STOP-LIMIT order (BONUS)")
        print("4) Get mark price")
        print("0) Exit")

        choice = input("Select an option: ").strip()

        if choice == "0":
            print("Exiting. Bye!")
            break

        elif choice == "1":
            print("\n--- MARKET ORDER ---")
            symbol = _read_symbol()
            side = _read_side()
            qty = float(_read_decimal("Quantity: "))

            resp = bot.place_market_order(symbol, side, qty)
            print_order_result(resp)

        elif choice == "2":
            print("\n--- LIMIT ORDER ---")
            symbol = _read_symbol()
            side = _read_side()
            qty = float(_read_decimal("Quantity: "))
            price = float(_read_decimal("Limit price: "))

            resp = bot.place_limit_order(symbol, side, qty, price)
            print_order_result(resp)

        elif choice == "3":
            print("\n--- STOP-LIMIT ORDER ---")
            symbol = _read_symbol()
            side = _read_side()
            qty = float(_read_decimal("Quantity: "))
            stop_price = float(_read_decimal("Stop price (trigger): "))
            limit_price = float(_read_decimal("Limit price (executed): "))

            resp = bot.place_stop_limit_order(symbol, side, qty, stop_price, limit_price)
            print_order_result(resp)

        elif choice == "4":
            print("\n--- MARK PRICE ---")
            symbol = _read_symbol()
            price_info = bot.get_symbol_price(symbol)
            if price_info:
                print(f"Mark price for {symbol}: {price_info.get('markPrice')}")
            else:
                print("Failed to fetch mark price.")

        else:
            print("Invalid choice, please try again.")


if __name__ == "__main__":
    main()

