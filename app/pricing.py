"""Precios por modelo y costo de cada llamada."""

import json
from pathlib import Path
from typing import Dict

TOKENS_PER_PRICE_UNIT = 1_000_000


class PriceTable:
    """Tabla de precios en USD por millón de tokens.

    :param path: Ruta de ``model_prices.json``.
    :type path: pathlib.Path or str
    :raises ValueError: Si el JSON o su forma son inválidos.
    :raises OSError: Si el archivo no se puede leer.
    """

    def __init__(self, path) -> None:
        text = Path(path).read_text(encoding="utf-8")
        try:
            data = json.loads(text)
            models = data["models"]
            self._prices: Dict[str, tuple] = {
                name: (float(price["input"]), float(price["output"]))
                for name, price in models.items()
            }
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise ValueError(f"invalid price file {path}") from error

    def __contains__(self, model: str) -> bool:
        return model in self._prices

    def cost_usd(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False,
    ) -> float:
        """Calcula el costo de una llamada; una llamada cacheada cuesta 0.

        :param model: Nombre del modelo.
        :type model: str
        :param input_tokens: Tokens de entrada.
        :type input_tokens: int
        :param output_tokens: Tokens de salida.
        :type output_tokens: int
        :param cached: Si la llamada salió del caché.
        :type cached: bool
        :return: Costo en USD, sin redondear.
        :rtype: float
        :raises ValueError: Si el modelo no tiene precio.
        """
        if model not in self._prices:
            raise ValueError(f"no price for model {model!r}")
        if cached:
            return 0.0
        price_in, price_out = self._prices[model]
        total = input_tokens * price_in + output_tokens * price_out
        return total / TOKENS_PER_PRICE_UNIT
