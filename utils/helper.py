# import yfinance as yf

# def search_symbols(search_term: str):
#     """
#     Search Yahoo Finance for tickers based on company name.
#     Returns a list of tuples: (label_to_show, value_to_return)
#     """
#     if not search_term or len(search_term) < 2:
#         return []

#     try:
#         # yf.Search performs a real-time lookup
#         search = yf.Search(search_term, max_results=8)
        
#         # We want to show "Apple Inc. (AAPL)" but return just "AAPL"
#         results = [
#             (f"{q['longname']} ({q['symbol']})", q['symbol']) 
#             for q in search.quotes 
#             if 'longname' in q and 'symbol' in q
#         ]
#         return results
#     except Exception:
#         return []
import json
def load_query_bundles(file_path="query_bundles.json"):
    try:
        with open(file_path, "r") as f:
            bundles = json.load(f)
        return bundles
    except FileNotFoundError:
        print("Error: The query bundle file was not found.")
        return []