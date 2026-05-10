# ioffe_db.py
from dataclasses import dataclass, field
from typing import Any, Dict

E_MASS = 9.1093837015e-31
E_CHARGE = 1.602176634e-19


def _resolve(value, ctx):
    return value(ctx) if callable(value) else value


def _check_fraction(ctx, key):
    if key in ctx and ctx[key] is not None:
        val = ctx[key]
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"{key} deve estar entre 0 e 1.")


@dataclass
class MaterialSpec:
    key: str
    source_url: str
    temperature_K: int
    structure: str
    name: Any
    props: Dict[str, Any]
    notes: str = ""

    def build(self, **ctx):
        _check_fraction(ctx, "x")
        _check_fraction(ctx, "y")

        return {
            "kind": "material",
            "key": self.key,
            "name": _resolve(self.name, ctx),
            "source_url": self.source_url,
            "temperature_K": self.temperature_K,
            "structure": self.structure,
            "notes": self.notes,
            "props": {k: _resolve(v, ctx) for k, v in self.props.items()},
        }


@dataclass
class PairSpec:
    key: str
    barrier_key: str
    well_key: str
    source_url: str
    name: Any
    props: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def build(self, materials, **ctx):
        barrier = materials[self.barrier_key].build(**ctx)
        well = materials[self.well_key].build(**ctx)

        pair_ctx = {
            **ctx,
            "barrier": barrier["props"],
            "well": well["props"],
        }

        pair_props = {k: _resolve(v, pair_ctx) for k, v in self.props.items()}

        # Derivados genéricos
        if (
            "pot_barrier_eV" not in pair_props
            and "electron_affinity_eV" in barrier["props"]
            and "electron_affinity_eV" in well["props"]
        ):
            pair_props["pot_barrier_eV"] = (
                well["props"]["electron_affinity_eV"]
                - barrier["props"]["electron_affinity_eV"]
            )

        if "pot_well_eV" not in pair_props:
            pair_props["pot_well_eV"] = 0.0

        if (
            "m_eff_ct_barrier_kg" not in pair_props
            and "m_eff_gamma_me" in barrier["props"]
        ):
            pair_props["m_eff_ct_barrier_kg"] = (
                barrier["props"]["m_eff_gamma_me"] * E_MASS
            )

        if (
            "m_eff_ct_well_kg" not in pair_props
            and "m_eff_gamma_me" in well["props"]
        ):
            pair_props["m_eff_ct_well_kg"] = (
                well["props"]["m_eff_gamma_me"] * E_MASS
            )

        return {
            "kind": "pair",
            "key": self.key,
            "name": _resolve(self.name, ctx),
            "source_url": self.source_url,
            "notes": self.notes,
            "barrier": barrier,
            "well": well,
            "props": pair_props,
        }


MATERIALS = {
    "gaas": MaterialSpec(
        key="gaas",
        source_url="https://www.ioffe.ru/SVA/NSM/Semicond/GaAs/basic.html",
        temperature_K=300,
        structure="Zinc Blende (Td^2-F43m)",
        name="GaAs",
        props={
            "latpar_m": 5.65325e-10,
            "density_g_cm3": 5.32,
            "debye_K": 360.0,
            "dielectric_static": 12.90,
            "dielectric_high": 10.89,
            "m_eff_gamma_me": 0.063,
            "electron_affinity_eV": 4.07,
            "optical_phonon_meV": 35.0,
            "Eg_eV": 1.519,
        },
    ),

    "algaas": MaterialSpec(
        key="algaas",
        source_url="https://www.ioffe.ru/SVA/NSM/Semicond/AlGaAs/basic.html",
        temperature_K=300,
        structure="Zinc Blende (Td^2-F43m)",
        name=lambda c: f"Al{c['x']:.3g}Ga{1-c['x']:.3g}As",
        props={
            "latpar_m": lambda c: (5.6533 + 0.0078 * c["x"]) * 1e-10,
            "density_g_cm3": lambda c: 5.32 - 1.56 * c["x"],
            "debye_K": lambda c: 370 + 54 * c["x"] + 22 * (c["x"] ** 2),
            "dielectric_static": lambda c: 12.90 - 2.84 * c["x"],
            "dielectric_high": lambda c: 10.89 - 2.73 * c["x"],
            "optical_phonon_meV": lambda c: (
                36.25 + 1.83 * c["x"] + 17.12 * (c["x"] ** 2) - 5.11 * (c["x"] ** 3)
            ),
            "m_eff_gamma_me": lambda c: (
                0.063 + 0.083 * c["x"] if c["x"] < 0.45 else 0.26
            ),
            "electron_affinity_eV": lambda c: (
                4.07 - 1.1 * c["x"] if c["x"] < 0.45 else 3.64 - 0.14 * c["x"]
            ),
            "Eg_eV": lambda c: 1.519 + 1.58 * c["x"],
        },
        notes="Usa as expressões da página basic; massa e afinidade são por trechos.",
    ),

    "inp": MaterialSpec(
        key="inp",
        source_url="https://www.ioffe.ru/SVA/NSM/Semicond/InP/basic.html",
        temperature_K=300,
        structure="Zinc Blende (Td^2-F43m)",
        name="InP",
        props={
            "latpar_m": 5.8687e-10,
            "density_g_cm3": 4.81,
            "debye_K": 425.0,
            "dielectric_static": 12.5,
            "dielectric_high": 9.61,
            "m_eff_gamma_me": 0.08,
            "electron_affinity_eV": 4.38,
            "optical_phonon_meV": 43.0,
            "Eg_eV": 1.344,
        },
    ),

    "gainas_lm_inp": MaterialSpec(
        key="gainas_lm_inp",
        source_url="https://www.ioffe.ru/SVA/NSM/Semicond/GaInAs/basic.html",
        temperature_K=300,
        structure="Zinc Blende (Td^2-F43m)",
        name="Ga0.47In0.53As",
        props={
            "latpar_m": 5.8687e-10,
            "density_g_cm3": 5.50,
            "debye_K": 330.0,
            "dielectric_static": 13.9,
            "dielectric_high": 11.6,
            "m_eff_gamma_me": 0.041,
            "electron_affinity_eV": 4.5,
            "optical_phonon_meV": 34.0,
            "Eg_eV": 0.74,
        },
        notes="Composição casada em rede com InP.",
    ),
}


PAIRS = {
    "algaas-gaas": PairSpec(
        key="algaas-gaas",
        barrier_key="algaas",
        well_key="gaas",
        source_url="https://www.ioffe.ru/SVA/NSM/Semicond/AlGaAs/basic.html",
        name=lambda c: f"Al{c['x']:.3g}Ga{1-c['x']:.3g}As / GaAs",
        props={
            "e_nonparab_barrier_J": lambda c: (
                (1.519 + 1.58 * c["x"]) * E_CHARGE
            ),
            "e_nonparab_well_J": 1.519 * E_CHARGE,
        },
    ),

    "gainas-inp": PairSpec(
        key="gainas-inp",
        barrier_key="inp",
        well_key="gainas_lm_inp",
        source_url="https://www.ioffe.ru/SVA/NSM/Semicond/GaInAs/bandstr.html",
        name="Ga0.47In0.53As / InP",
        props={
            "delta_ec_eV": 0.22,
            "delta_ev_eV": 0.38,
        },
        notes="Offsets de banda do Ioffe para Ga0.47In0.53As/InP.",
    ),
}


def list_materials():
    return sorted(MATERIALS.keys())


def list_pairs():
    return sorted(PAIRS.keys())


def build_material(key, **ctx):
    return MATERIALS[key].build(**ctx)


def build_pair(key, **ctx):
    return PAIRS[key].build(MATERIALS, **ctx)