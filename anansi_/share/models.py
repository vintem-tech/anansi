from .settings import Exchange

class MarketModel:
    exchange:Exchange = None
    quote_symbol = ""
    base_symbol = ""

    def asset_symbol(self):
        return self.quote_symbol + self.asset_symbol


class KlinesModel:
    pass