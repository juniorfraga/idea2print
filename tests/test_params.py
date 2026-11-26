import pytest

from idea2print.params import ParamError, load_params


def write(tmp_path, text):
    f = tmp_path / "params.toml"
    f.write_text(text)
    return f


FULL = """
[medidas.vial_diameter]
valor = 16.0
origem = "estimada"
nota = "frasco 3 mL, medir com paquimetro"

[medidas.cup_diameter]
valor = 99.0
origem = "projeto"
fonte = "https://makerworld.com/x"
"""


def test_loads_value_origin_source(tmp_path):
    p = load_params(write(tmp_path, FULL))
    assert p.v("cup_diameter") == 99.0
    assert p["cup_diameter"].origin == "projeto"
    assert p["cup_diameter"].source.startswith("https://")


def test_estimated_lists_keys(tmp_path):
    assert load_params(write(tmp_path, FULL)).estimated() == ["vial_diameter"]


def test_missing_origin_names_key(tmp_path):
    with pytest.raises(ParamError, match="x"):
        load_params(write(tmp_path, "[medidas.x]\nvalor = 1\n"))


def test_invalid_origin_rejected(tmp_path):
    with pytest.raises(ParamError, match="chute"):
        load_params(write(tmp_path, '[medidas.x]\nvalor = 1\norigem = "chute"\n'))


def test_projeto_requires_fonte(tmp_path):
    with pytest.raises(ParamError, match="fonte"):
        load_params(write(tmp_path, '[medidas.x]\nvalor = 1\norigem = "projeto"\n'))


def test_printer_defaults_and_override(tmp_path):
    p = load_params(write(tmp_path, FULL))
    assert p.printer.bed_mm == (256, 256, 256)
    assert p.printer.min_wall_mm == 1.2
    assert p.printer.max_overhang_deg == 45.0
    q = load_params(write(tmp_path, FULL + "\n[impressao]\nbed_mm = [180, 180, 180]\n"))
    assert q.printer.bed_mm == (180, 180, 180)


def test_non_table_measurement_rejected(tmp_path):
    with pytest.raises(ParamError, match="x"):
        load_params(write(tmp_path, "[medidas]\nx = 5\n"))


@pytest.mark.parametrize("body", ["bed_mm = [1, 2]", "min_wall_mm = -1", "max_overhang_deg = 90"])
def test_invalid_printer_limits_rejected(tmp_path, body):
    with pytest.raises(ParamError, match="impressao"):
        load_params(write(tmp_path, f"[impressao]\n{body}\n"))
