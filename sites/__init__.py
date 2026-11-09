"""Registro de scrapers por web. Cada modulo expone buscar(marca, modelos_busqueda, modelo_id) -> list[Listing]."""
from . import autofesa, canalcar, clicars, coches_com, ftomeocasion, ocasionplus

SCRAPERS = {
    ftomeocasion.WEB_ID: ftomeocasion.buscar,
    canalcar.WEB_ID: canalcar.buscar,
    coches_com.WEB_ID: coches_com.buscar,
    clicars.WEB_ID: clicars.buscar,
    autofesa.WEB_ID: autofesa.buscar,
    ocasionplus.WEB_ID: ocasionplus.buscar,
}
