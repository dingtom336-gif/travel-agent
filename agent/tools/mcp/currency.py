# Currency conversion MCP tool - fawazahmed0 (primary) + hardcoded fallback
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_CURRENCY_API_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies"
_CURRENCY_TIMEOUT = 3.0


# Hardcoded exchange rates relative to CNY (1 CNY = X foreign)
# Last mock update: 2026-02-01
_RATES_TO_CNY: Dict[str, float] = {
  "CNY": 1.0,
  "USD": 0.137,
  "EUR": 0.126,
  "GBP": 0.108,
  "JPY": 20.45,
  "KRW": 184.5,
  "THB": 4.78,
  "SGD": 0.184,
  "HKD": 1.072,
  "TWD": 4.38,
  "MYR": 0.639,
  "VND": 3456,
  "PHP": 7.72,
  "IDR": 2158,
  "AUD": 0.212,
  "NZD": 0.232,
  "CAD": 0.189,
  "CHF": 0.122,
  "RUB": 12.6,
  "INR": 11.5,
}

# Currency display info
_CURRENCY_INFO: Dict[str, Dict[str, str]] = {
  "CNY": {"name": "人民币", "symbol": "¥", "name_en": "Chinese Yuan"},
  "USD": {"name": "美元", "symbol": "$", "name_en": "US Dollar"},
  "EUR": {"name": "欧元", "symbol": "€", "name_en": "Euro"},
  "GBP": {"name": "英镑", "symbol": "£", "name_en": "British Pound"},
  "JPY": {"name": "日元", "symbol": "¥", "name_en": "Japanese Yen"},
  "KRW": {"name": "韩元", "symbol": "₩", "name_en": "Korean Won"},
  "THB": {"name": "泰铢", "symbol": "฿", "name_en": "Thai Baht"},
  "SGD": {"name": "新加坡元", "symbol": "S$", "name_en": "Singapore Dollar"},
  "HKD": {"name": "港币", "symbol": "HK$", "name_en": "Hong Kong Dollar"},
  "TWD": {"name": "新台币", "symbol": "NT$", "name_en": "Taiwan Dollar"},
  "MYR": {"name": "马来西亚林吉特", "symbol": "RM", "name_en": "Malaysian Ringgit"},
  "VND": {"name": "越南盾", "symbol": "₫", "name_en": "Vietnamese Dong"},
  "PHP": {"name": "菲律宾比索", "symbol": "₱", "name_en": "Philippine Peso"},
  "IDR": {"name": "印尼盾", "symbol": "Rp", "name_en": "Indonesian Rupiah"},
  "AUD": {"name": "澳元", "symbol": "A$", "name_en": "Australian Dollar"},
  "NZD": {"name": "新西兰元", "symbol": "NZ$", "name_en": "New Zealand Dollar"},
  "CAD": {"name": "加元", "symbol": "C$", "name_en": "Canadian Dollar"},
  "CHF": {"name": "瑞士法郎", "symbol": "CHF", "name_en": "Swiss Franc"},
  "RUB": {"name": "俄罗斯卢布", "symbol": "₽", "name_en": "Russian Ruble"},
  "INR": {"name": "印度卢比", "symbol": "₹", "name_en": "Indian Rupee"},
}


def _get_rate(from_currency: str, to_currency: str) -> Optional[float]:
  """Calculate exchange rate between two currencies via CNY."""
  from_to_cny = _RATES_TO_CNY.get(from_currency.upper())
  to_to_cny = _RATES_TO_CNY.get(to_currency.upper())
  if from_to_cny is None or to_to_cny is None:
    return None
  # from_currency -> CNY -> to_currency
  # 1 from_currency = (1 / from_to_cny) CNY = (1 / from_to_cny) * to_to_cny to_currency
  return to_to_cny / from_to_cny


async def convert_currency(
  amount: float,
  from_currency: str,
  to_currency: str,
) -> Dict[str, Any]:
  """Convert amount between currencies.

  Fallback: fawazahmed0 API (via jsdelivr CDN) → hardcoded rates.
  """
  from_code = from_currency.upper()
  to_code = to_currency.upper()
  source = "hardcoded"

  # 1. Try fawazahmed0 real-time rates (CDN, 341 currencies)
  rate = None
  try:
    rate = await _fetch_live_rate(from_code, to_code)
    if rate:
      source = "fawazahmed0"
  except Exception as exc:
    logger.debug("Currency API failed: %s", exc)

  # 2. Hardcoded fallback
  if rate is None:
    rate = _get_rate(from_code, to_code)

  if rate is None:
    return {
      "success": False,
      "error": f"Unsupported currency pair: {from_code}/{to_code}",
      "supported_currencies": list(_RATES_TO_CNY.keys()),
    }

  converted_amount = round(amount * rate, 2)
  from_info = _CURRENCY_INFO.get(from_code, {"name": from_code, "symbol": from_code, "name_en": from_code})
  to_info = _CURRENCY_INFO.get(to_code, {"name": to_code, "symbol": to_code, "name_en": to_code})

  return {
    "success": True,
    "source": source,
    "from": {
      "currency": from_code,
      "name": from_info["name"],
      "symbol": from_info["symbol"],
      "amount": amount,
      "display": f"{from_info['symbol']}{amount:,.2f}",
    },
    "to": {
      "currency": to_code,
      "name": to_info["name"],
      "symbol": to_info["symbol"],
      "amount": converted_amount,
      "display": f"{to_info['symbol']}{converted_amount:,.2f}",
    },
    "rate": round(rate, 6),
    "rate_display": f"1 {from_code} = {round(rate, 4)} {to_code}",
    "note": "汇率仅供参考，实际交易以银行当日牌价为准",
  }


async def _fetch_live_rate(from_code: str, to_code: str) -> Optional[float]:
  """Fetch real-time exchange rate from fawazahmed0 API via CDN."""
  from_lower = from_code.lower()
  to_lower = to_code.lower()
  url = f"{_CURRENCY_API_URL}/{from_lower}.json"

  try:
    async with httpx.AsyncClient(timeout=_CURRENCY_TIMEOUT) as client:
      resp = await client.get(url)
      resp.raise_for_status()
      data = resp.json()

    rates = data.get(from_lower, {})
    rate = rates.get(to_lower)
    if rate is not None:
      logger.info("Currency API: %s→%s = %s", from_code, to_code, rate)
      return float(rate)
    return None
  except Exception as exc:
    logger.debug("Currency API error: %s", exc)
    return None


async def list_supported_currencies() -> Dict[str, Any]:
  """List all supported currencies with their info.

  Returns:
    Dict with list of supported currencies
  """
  try:
    currencies = []
    for code, rate in _RATES_TO_CNY.items():
      info = _CURRENCY_INFO.get(code, {"name": code, "symbol": code, "name_en": code})
      currencies.append({
        "code": code,
        "name": info["name"],
        "name_en": info["name_en"],
        "symbol": info["symbol"],
        "rate_to_cny": round(1 / rate, 4) if rate > 0 else 0,
      })
    return {
      "success": True,
      "currencies": currencies,
      "base_currency": "CNY",
    }
  except Exception as exc:
    return {
      "success": False,
      "error": str(exc),
    }
