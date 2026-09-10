"""Medication access capabilities; stock observations are never dispensations."""

from omnisus_db.sources.medicamentos.horus import StockPage, fetch_stock_page

__all__ = ["StockPage", "fetch_stock_page"]
