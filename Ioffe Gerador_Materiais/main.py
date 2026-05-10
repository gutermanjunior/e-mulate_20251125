# main.py
import argparse
import getpass
from datetime import datetime

from ioffe_db import (
    build_material,
    build_pair,
    list_materials,
    list_pairs,
)


def fmt_value(v):
    if isinstance(v, float):
        if v == 0:
            return "0.0"
        if abs(v) < 1e-3 or abs(v) >= 1e4:
            return f"{v:.16e}"
        return f"{v:.6f}"
    return str(v)


def header_lines(title, source_url, temperature_K, structure, notes=""):
    try:
        usuario = getpass.getuser()
    except Exception:
        usuario = "Desenvolvedor"

    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "#" * 100,
        f"# BLOCO:         {title}",
        "# DESCRIÇÃO:     Parâmetros físicos e eletrônicos para simulação.",
        "# FONTE:         Ioffe Institute - NSM Archive",
        f"# URL DA FONTE:  {source_url}",
        f"# TEMPERATURA:   {temperature_K} K",
        f"# ESTRUTURA:     {structure}",
        f"# GERADO POR:    {usuario}",
        f"# DATA/HORA:     {data_hora}",
    ]
    if notes:
        lines.append(f"# OBSERVAÇÕES:   {notes}")
    lines.append("#" * 100)
    return lines


def format_material_block(material):
    lines = header_lines(
        title=material["name"],
        source_url=material["source_url"],
        temperature_K=material["temperature_K"],
        structure=material["structure"],
        notes=material.get("notes", ""),
    )

    lines.append(f"[{material['key']}]")
    for key, value in material["props"].items():
        lines.append(f"{key} = {fmt_value(value)}")

    return "\n".join(lines)


def format_pair_block(pair):
    barrier = pair["barrier"]
    well = pair["well"]
    props = pair["props"]

    lines = header_lines(
        title=pair["name"],
        source_url=pair["source_url"],
        temperature_K=barrier["temperature_K"],
        structure=barrier["structure"],
        notes=pair.get("notes", ""),
    )

    lines.append(f"[{pair['key']}]")

    if "latpar_m" in barrier["props"]:
        lines.append(f"latpar = {fmt_value(barrier['props']['latpar_m'])}")

    lines.append("")
    lines.append(f"barrier = {barrier['name']}")
    if "m_eff_ct_barrier_kg" in props:
        lines.append(f"m_eff_ct_barrier = {fmt_value(props['m_eff_ct_barrier_kg'])}")
    if "pot_barrier_eV" in props:
        lines.append(f"pot_barrier = {fmt_value(props['pot_barrier_eV'])}")

    for extra in ("delta_ec_eV", "delta_ev_eV", "e_nonparab_barrier_J"):
        if extra in props:
            lines.append(f"{extra} = {fmt_value(props[extra])}")

    lines.append("")
    lines.append(f"well = {well['name']}")
    if "m_eff_ct_well_kg" in props:
        lines.append(f"m_eff_ct_well = {fmt_value(props['m_eff_ct_well_kg'])}")
    if "pot_well_eV" in props:
        lines.append(f"pot_well = {fmt_value(props['pot_well_eV'])}")

    if "e_nonparab_well_J" in props:
        lines.append(f"e_nonparab_well_J = {fmt_value(props['e_nonparab_well_J'])}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Gerador de materiais semicondutores com base Ioffe."
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    p_list = subparsers.add_parser("list", help="Lista materiais e pares disponíveis")

    p_mat = subparsers.add_parser("material", help="Gera um bloco de material")
    p_mat.add_argument("key", help="Chave do material")
    p_mat.add_argument("--x", type=float, default=None)
    p_mat.add_argument("--y", type=float, default=None)

    p_pair = subparsers.add_parser("pair", help="Gera um bloco de heteroestrutura")
    p_pair.add_argument("key", help="Chave do par")
    p_pair.add_argument("--x", type=float, default=None)
    p_pair.add_argument("--y", type=float, default=None)

    args = parser.parse_args()

    if args.mode == "list":
        print("Materiais disponíveis:")
        for k in list_materials():
            print(f"  - {k}")

        print("\nPares disponíveis:")
        for k in list_pairs():
            print(f"  - {k}")
        return

    ctx = {"x": args.x, "y": args.y}

    if args.mode == "material":
        block = build_material(args.key, **ctx)
        print(format_material_block(block))
        return

    if args.mode == "pair":
        block = build_pair(args.key, **ctx)
        print(format_pair_block(block))
        return


if __name__ == "__main__":
    main()