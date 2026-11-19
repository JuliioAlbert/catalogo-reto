"""Catálogo de productos de solo lectura."""

import json
from pathlib import Path
from typing import Optional


class Catalog:
    """Productos cargados de un archivo JSON.

    :param path: Ruta del archivo ``products.json``.
    :type path: str or Path
    :raises OSError: Si el archivo no se puede leer.
    :raises ValueError: Si el contenido no es una lista JSON.
    """

    def __init__(self, path) -> None:
        with Path(path).open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("products file must contain a JSON list")
        self._products = tuple(data)

    def get_product(self, product_id: str) -> Optional[dict]:
        """Busca un producto por id.

        :param product_id: Id, por ejemplo ``PRD-0004``.
        :type product_id: str
        :return: El producto o ``None`` si no existe.
        :rtype: dict or None
        """
        wanted = str(product_id).strip().upper()
        for product in self._products:
            if product.get("id", "").upper() == wanted:
                return dict(product)
        return None

    def search_by_category(self, category: str) -> list:
        """Lista los productos de una categoría, sin distinguir mayúsculas.

        :param category: Nombre de la categoría.
        :type category: str
        :return: Los productos de la categoría (puede estar vacía).
        :rtype: list[dict]
        """
        wanted = str(category).strip().casefold()
        return [
            dict(e)
            for e in self._products
            if e.get("category", "").casefold() == wanted
        ]

    def list_products(self, category=None, status=None, in_stock=None) -> list:
        """Lista productos con filtros opcionales.

        :param category: Categoría, sin distinguir mayúsculas; ``None`` para todas.
        :type category: str or None
        :param status: ``activo`` o ``descontinuado``; ``None`` para ambos.
        :type status: str or None
        :param in_stock: ``True`` solo con existencias, ``False`` solo agotados.
        :type in_stock: bool or None
        :return: Productos que cumplen todos los filtros dados.
        :rtype: list[dict]
        """
        wanted = str(category).strip().casefold() if category else None
        found = []
        for product in self._products:
            if wanted and product.get("category", "").casefold() != wanted:
                continue
            if status and product.get("status") != status:
                continue
            if in_stock is not None and (product.get("stock", 0) > 0) != in_stock:
                continue
            found.append(dict(product))
        return found

    def categories(self) -> list:
        """Nombres de las categorías que existen en los datos.

        :return: Nombres sin repetir.
        :rtype: list[str]
        """
        names = {e.get("category", "") for e in self._products}
        return sorted(name for name in names if name)
