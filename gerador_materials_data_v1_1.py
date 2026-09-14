#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gerador_materials_data_v1_1.py
==============================

Gerador auditável de blocos de materiais para o e⁻mulate
Projeto: Quantum Bragg Mirror Detectors (QBM)
Versão: 1.1.0
Data: 2026-09-14

OBJETIVO
--------
Perguntar ao usuário:
    1. qual modelo de materiais deseja usar;
    2. qual a porcentagem de Al na barreira;
    3. qual a porcentagem de Al no poço (Enter = GaAs);
    4. quando necessário, qual a temperatura;

e produzir um bloco pronto para ser adicionado ao arquivo ``materials.data``
do e⁻mulate.

PRINCÍPIO DE PROVENIÊNCIA
-------------------------
Este programa segue a cadeia:

    valor numérico
      -> fórmula executada
      -> entradas
      -> fonte
      -> localizador exato na fonte
      -> derivação/adaptação, quando houver
      -> campo do materials.data

As fórmulas que aparecem abaixo NÃO são tratadas todas da mesma maneira.
Os comentários distinguem explicitamente:

    DIRECT_FROM_SOURCE
        A fórmula/valor aparece diretamente na fonte.

    DERIVED_FROM_SOURCE
        A expressão usada pelo programa é uma dedução algébrica de dados
        fornecidos pela fonte.

    MODEL_CHOICE
        Há uma escolha física adicional do projeto.

    EMULATE_MAPPING
        Uma grandeza da fonte é mapeada para um campo específico do e⁻mulate.

    EMULATE_ADAPTATION
        É necessária uma adaptação numérica para representar o modelo no solver.

    LINEAR_EXTENSION
        Uma parametrização linear é estendida para uma heteroestrutura entre
        duas ligas, em vez de apenas GaAs/AlGaAs.

    HISTORICAL_PARAMETERIZATION
        O objetivo é reproduzir uma parametrização histórica, não reconstruir
        a fonte científica primária.

ESCOPO DESTA VERSÃO
-------------------
Modelos habilitados:

    1. Ioffe — Direct Heterointerface / Eg_as_Enp
    2. Ioffe — Anderson Affinity / Eg_as_Enp
    3. Schneider/Liu — CBO087 One-Band
    4. Schneider/Liu — Two-Band 2007
    5. Vurgaftman et al. (2001) — Gamma-KaneLinearized
    6. GMP — Vurgaftman Historical 2022-10-07

NÃO entram automaticamente nesta versão os conjuntos Fernando/GMP que possuem
conflitos entre fórmulas e valores literais. A regra adotada é conservadora:
se a origem/interpretação ainda estiver duvidosa, o programa não a transforma
em parametrização canônica.

REFERÊNCIA DO SOLVER
--------------------
e⁻mulate / LabSem-PUC-Rio
Commit de referência auditado:
    39529427998b68db8b170319547b1d35f227419a

Arquivos auditados:
    e-mulate.py
    simdata.py
    simcore.py

Pontos relevantes do solver:
    - ``simcore.py``, linhas 7–10:
        E_CHARGE, E_MASS e HBAR.
    - ``simcore.py``, linha 94 (rotina de busca) e linha 407
      (TransferMatrix):
        m(E) = m_cte * [1 + (E - V) / E_np]
    - ``simdata.py``, linhas 324–327:
        dx em nm -> conversão direta para metros;
        dx em ML -> usa ``latpar / 2``.
      Portanto, para geometrias e dx definidos em nm, ``latpar`` não entra
      diretamente no cálculo dos autovalores do fluxo auditado.

UNIDADES
--------
Entrada:
    composição de Al: porcentagem (%)
    temperatura: kelvin (K)

Saída para materials.data:
    latpar              : metro (m)
    m_eff_ct_*          : quilograma (kg)
    pot_*               : elétron-volt (eV)
    e_nonparab_*        : joule (J)

REQUISITOS
----------
Python >= 3.10
Somente biblioteca padrão.

USO
---
Interativo:
    python gerador_materials_data_v1_1.py

Listar modelos:
    python gerador_materials_data_v1_1.py --list-models

Executar testes internos:
    python gerador_materials_data_v1_1.py --self-test

OBSERVAÇÃO SOBRE CITAÇÕES
-------------------------
Para páginas HTML do Ioffe não existe paginação impressa. Nesses casos o
localizador é dado por arquivo/página HTML + seção/tabela.

Para o caderno do GMP, a fonte disponível é uma transcrição organizada por
data (``Texto colado.txt``); não existe página estável, então o localizador é
a data da anotação.

Este arquivo é código científico de apoio ao projeto e deve ser versionado
junto com a matriz canônica de parametrizações usada para documentar cada
simulação.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Callable, Final


__version__ = "1.1.0"


# ============================================================================
# Constantes físicas
# ============================================================================
#
# Fonte no próprio solver auditado:
#   arquivo: simcore.py
#   linhas: 7–10
#
# Esses valores também correspondem às constantes SI exatas/recomendadas
# usadas pelo e⁻mulate de referência.
#
E_CHARGE: Final[float] = 1.602176634e-19  # C = J/eV
M0: Final[float] = 9.1093837015e-31      # kg
ANGSTROM: Final[float] = 1.0e-10         # m


# ============================================================================
# Registro documental das fontes
# ============================================================================

@dataclass(frozen=True)
class SourceReference:
    """Identificação humana e auditável de uma fonte científica/histórica."""

    source_id: str
    source: str
    local_file: str
    locator: str
    notes: str = ""


SOURCES: Final[dict[str, SourceReference]] = {
    "IOFFE_ALGAAS_BASIC": SourceReference(
        source_id="IOFFE_ALGAAS_BASIC",
        source="Ioffe Institute NSM Archive — AlGaAs, Basic Parameters",
        local_file="Ioffe-AlGaAs.zip -> .../AlGaAs/basic.html",
        locator=(
            "HTML sem paginação; seção/tabela 'Basic Parameters at 300 K'. "
            "Entradas usadas: lattice constant, effective electron mass, "
            "electron affinity."
        ),
        notes=(
            "Página usada para a(x), m*_Gamma(x) e chi(x). "
            "Faixas de composição devem ser respeitadas conforme a página."
        ),
    ),
    "IOFFE_ALGAAS_BAND": SourceReference(
        source_id="IOFFE_ALGAAS_BAND",
        source="Ioffe Institute NSM Archive — AlGaAs, Band Structure",
        local_file="Ioffe-AlGaAs.zip -> .../AlGaAs/bandstr.html",
        locator=(
            "HTML sem paginação; seção 'Band Discontinuities at "
            "AlxGa1-xAs/GaAs Heterointerface' e seção de energy gap."
        ),
        notes=(
            "Página usada para Eg(x) e para o offset de condução piecewise."
        ),
    ),
    "IOFFE_GAAS_BASIC": SourceReference(
        source_id="IOFFE_GAAS_BASIC",
        source="Ioffe Institute NSM Archive — GaAs, Basic Parameters",
        local_file="Ioffe-GaAs www.ioffe.ru.zip -> .../GaAs/basic.html",
        locator="HTML sem paginação; tabela de Basic Parameters.",
        notes="Endpoint GaAs; a_GaAs = 5.65325 Å na página específica de GaAs.",
    ),
    "SCHNEIDER_LIU_2007": SourceReference(
        source_id="SCHNEIDER_LIU_2007",
        source=(
            "H. Schneider, H. C. Liu, Quantum Well Infrared Photodetectors: "
            "Physics and Applications, Springer, 2007"
        ),
        local_file=(
            "Quantum Well Infrared Photodetectors-Physics and "
            "Applications - Copia.pdf"
        ),
        locator=(
            "p. 17, §3.2; p. 37, §3.4.4; p. 38; "
            "p. 73, §4.4 (páginas impressas do livro)."
        ),
        notes="Fonte dos modelos one-band e empirical two-band.",
    ),
    "VURGAFTMAN_2001": SourceReference(
        source_id="VURGAFTMAN_2001",
        source=(
            "I. Vurgaftman, J. R. Meyer, L. R. Ram-Mohan, "
            "'Band parameters for III-V compound semiconductors and their "
            "alloys', J. Appl. Phys. 89, 5815–5875 (2001), "
            "DOI 10.1063/1.1368156"
        ),
        local_file=(
            "Vurgaftman - Band parameters for III-V compound "
            "semiconductors and their alloys.pdf"
        ),
        locator=(
            "Eq. (2.13) p. 5818; Eq. (2.15) p. 5819; "
            "Table I p. 5825; Table II p. 5826; "
            "Sec. IV p. 5837; Table XII p. 5838; "
            "Sec. VI-A p. 5855."
        ),
        notes=(
            "A saída desta ferramenta é uma redução Gamma/Kane linearizada "
            "para o campo escalar e_nonparab do e⁻mulate; não é um solver "
            "multibanda completo."
        ),
    ),
    "GMP_20221007": SourceReference(
        source_id="GMP_20221007",
        source="Caderno de Germano Maioli Penello (GMP)",
        local_file="Texto colado.txt",
        locator=(
            "Anotação de 07/10/2022 ('Dados para GaAs/AlAs segundo "
            "Vurgaftman') e aplicação de 10/10/2022."
        ),
        notes=(
            "Fonte histórica sem paginação estável. Serve para reproduzir "
            "a parametrização efetivamente usada pelo GMP, não para substituir "
            "o artigo Vurgaftman original."
        ),
    ),
    "EMULATE_SOLVER": SourceReference(
        source_id="EMULATE_SOLVER",
        source="Código-fonte do e⁻mulate auditado",
        local_file="simcore.py / simdata.py / e-mulate.py",
        locator=(
            "simcore.py linhas 7–10 (constantes); linha 94 e linha 407 "
            "(massa não parabólica); simdata.py linhas 324–327 (dx e latpar)."
        ),
        notes="Commit de referência: 39529427998b68db8b170319547b1d35f227419a.",
    ),
}


# ============================================================================
# Estrutura da saída
# ============================================================================

@dataclass(frozen=True)
class MaterialBlock:
    """Campos necessários para um bloco do materials.data."""

    model_id: str
    latpar: float
    m_barrier: float
    pot_barrier: float
    enp_barrier: float
    m_well: float
    pot_well: float
    enp_well: float
    warnings: tuple[str, ...] = ()


# ============================================================================
# Funções auxiliares
# ============================================================================

def fraction_string(x: float) -> str:
    """Converte uma fração em representação compacta para o nome do material."""

    return f"{x:.6f}".rstrip("0").rstrip(".")


def material_name(x: float) -> str:
    """Retorna GaAs, AlAs ou Al{x}Ga{1-x}As."""

    if math.isclose(x, 0.0, abs_tol=1e-12):
        return "GaAs"
    if math.isclose(x, 1.0, abs_tol=1e-12):
        return "AlAs"

    return f"Al{fraction_string(x)}Ga{fraction_string(1.0 - x)}As"


def scientific(value: float) -> str:
    """Formatação científica consistente para o materials.data."""

    return f"{value:.15E}"


def compact_number(value: float) -> str:
    """Formatação decimal compacta para potenciais em eV."""

    return f"{value:.12g}"


def read_percentage(prompt: str, *, default: float | None = None) -> float:
    """
    Lê porcentagem do usuário e devolve fração no intervalo [0, 1].

    Aceita vírgula decimal, por exemplo: ``20,7``.
    """

    text = input(prompt).strip().replace(",", ".")

    if not text:
        if default is None:
            raise ValueError("É necessário fornecer uma porcentagem.")
        return default

    value = float(text) / 100.0

    if not 0.0 <= value <= 1.0:
        raise ValueError("A porcentagem deve estar entre 0 e 100.")

    return value


def validate_barrier_well(x_well: float, x_barrier: float) -> None:
    """
    Valida apenas a convenção usada neste gerador.

    Para os QWIPs tratados neste projeto, a barreira deve possuir fração de Al
    maior ou igual à do poço.
    """

    if x_barrier < x_well:
        raise ValueError(
            "Esta versão espera x_barrier >= x_well. "
            "Revise qual camada é poço e qual é barreira."
        )


# ============================================================================
# Ioffe — grandezas bulk
# ============================================================================

def ioffe_lattice_parameter(x: float) -> float:
    """
    Parâmetro de rede do AlxGa1-xAs em metros.

    EQUAÇÃO
        a(x) = 5.6533 + 0.0078*x  [Å]

    ORIGEM
        [DIRECT_FROM_SOURCE]
        Arquivo/fonte:
            Ioffe-AlGaAs.zip -> .../AlGaAs/basic.html
        Localizador:
            HTML sem paginação;
            tabela/seção "Basic Parameters at 300 K";
            linha "Lattice constant".

    OBSERVAÇÃO DE MAPEAMENTO
        O materials.data possui um único campo ``latpar`` embora uma
        heteroestrutura possa ter dois parâmetros de rede.

        Nesta versão exportamos a(x_barrier), reproduzindo a política adotada
        na matriz canônica do projeto.

        [EMULATE_CONVENTION]

        A auditoria do solver mostrou que, quando larguras e dx são fornecidos
        em nm, latpar não entra diretamente nos autovalores:
            simdata.py, linhas 324–327.
    """

    return (5.6533 + 0.0078 * x) * ANGSTROM


def ioffe_effective_mass(x: float) -> float:
    """
    Massa efetiva Gamma do elétron no AlxGa1-xAs.

    EQUAÇÃO
        m*_Gamma(x) = (0.063 + 0.083*x) m0

    ORIGEM
        [DIRECT_FROM_SOURCE]
        Arquivo/fonte:
            Ioffe-AlGaAs.zip -> .../AlGaAs/basic.html
        Localizador:
            HTML sem paginação;
            tabela "Basic Parameters at 300 K";
            "Effective electron mass";
            domínio indicado: x < 0.45.

    A conversão m*/m0 -> kg é feita multiplicando por M0, cujo valor é o
    mesmo usado em simcore.py, linha 8.
    """

    if not 0.0 <= x < 0.45:
        raise ValueError(
            "A massa Ioffe usada nesta versão está documentada para 0 <= x < 0.45."
        )

    return (0.063 + 0.083 * x) * M0


def ioffe_energy_gap(x: float) -> float:
    """
    Energy gap usado no modelo Ioffe do projeto, em eV.

    EQUAÇÃO
        Eg(x) = 1.424 + 1.247*x  [eV]

    ORIGEM
        [DIRECT_FROM_SOURCE]
        Arquivo/fonte:
            Ioffe-AlGaAs.zip -> .../AlGaAs/bandstr.html
        Localizador:
            HTML sem paginação;
            seção/tabela de band structure / "Energy gap";
            domínio adotado: x < 0.45.

    IMPORTANTE
        A fonte fornece Eg(x).
        Ela NÃO declara que o parâmetro ``e_nonparab`` do e⁻mulate seja Eg.

        Quando o programa usa:
            E_np = Eg
        isso é:
            [EMULATE_MAPPING]

        e não uma equação atribuída ao Ioffe.
    """

    if not 0.0 <= x < 0.45:
        raise ValueError(
            "O Eg Ioffe usado nesta versão está documentado para 0 <= x < 0.45."
        )

    return 1.424 + 1.247 * x


def ioffe_direct_ec_relative_to_gaas(x: float) -> float:
    """
    Descontinuidade da banda de condução relativa ao GaAs, em eV.

    EQUAÇÕES
        para x < 0.41:
            ΔEc(x) = 0.79*x

        para x > 0.41:
            ΔEc(x) = 0.475 - 0.335*x + 0.143*x²

    ORIGEM
        [DIRECT_FROM_SOURCE]
        Arquivo/fonte:
            Ioffe-AlGaAs.zip -> .../AlGaAs/bandstr.html
        Localizador:
            HTML sem paginação;
            seção "Band Discontinuities at
            AlxGa1-xAs/GaAs Heterointerface".

    PARA POÇO AlGaAs
        O Ioffe escreve a descontinuidade em relação ao GaAs.
        Para uma heteroestrutura entre duas ligas, o programa usa:

            Vb = ΔEc(x_barrier) - ΔEc(x_well)

        Classificação:
            [DERIVED_FROM_SOURCE]

    CASO x = 0.41
        A fonte separa as expressões em x<0.41 e x>0.41.
        Para não inventar uma regra no ponto de fronteira, x=0.41 é rejeitado
        explicitamente nesta versão.

    CASO x = 0.42
        Por decisão documentada do projeto, usar o ramo x>0.41.
        A interpretação continua a ramificação Gamma no solver reduzido,
        registrando warning de região Gamma-X.
    """

    if math.isclose(x, 0.41, abs_tol=1e-12):
        raise ValueError(
            "x = 0.41 é exatamente a fronteira entre as duas expressões "
            "do offset Ioffe e não é usado automaticamente."
        )

    if x < 0.41:
        return 0.79 * x

    return 0.475 - 0.335 * x + 0.143 * x**2


def ioffe_anderson_offset(x_well: float, x_barrier: float) -> float:
    """
    Offset de condução pela regra de Anderson usando afinidades do Ioffe.

    DADO DA FONTE
        χ(x) = 4.07 - 1.1*x  [eV], para x < 0.45.

    ORIGEM DA AFINIDADE
        [DIRECT_FROM_SOURCE]
        Ioffe-AlGaAs.zip -> .../AlGaAs/basic.html
        HTML sem paginação;
        "Electron affinity", na tabela "Basic Parameters at 300 K".

    MODELO ADICIONAL
        Pela regra de Anderson:
            ΔEc = χ_well - χ_barrier

        portanto:
            ΔEc = 1.1 * (x_barrier - x_well)

    CLASSIFICAÇÃO
        Afinidade:
            [DIRECT_FROM_SOURCE]
        Construção do offset:
            [MODEL_CHOICE] + [DERIVED_FROM_SOURCE]

    ATENÇÃO
        Este NÃO é o offset direto dado pela seção de heterointerface do
        próprio Ioffe. Por isso aparece como modelo separado.
    """

    if not (0.0 <= x_well < 0.45 and 0.0 <= x_barrier < 0.45):
        raise ValueError(
            "A afinidade Ioffe usada nesta versão está documentada para x < 0.45."
        )

    return 1.1 * (x_barrier - x_well)


# ============================================================================
# Modelo 1 — Ioffe Direct Heterointerface / Eg_as_Enp
# ============================================================================

def model_ioffe_direct(x_well: float, x_barrier: float) -> MaterialBlock:
    """
    Modelo principal Ioffe adotado no projeto.

    pot_barrier
        Offset direto da seção de heterointerface do Ioffe.

    e_nonparab
        Eg(x) é direto do Ioffe, mas E_np = Eg é [EMULATE_MAPPING].

    Lei de massa do e⁻mulate que motiva o campo E_np:
        m(E) = m_cte * [1 + (E - V) / E_np]

    Fonte do solver:
        simcore.py, linha 94 e linha 407, no commit auditado.
    """

    validate_barrier_well(x_well, x_barrier)

    warnings: list[str] = []

    if x_well > 0.41 or x_barrier > 0.41:
        warnings.append(
            "Ioffe: composição acima de x=0.41. Foi usado o ramo quadrático "
            "de ΔEc e a simulação deve ser interpretada como continuação da "
            "ramificação Gamma na região de crossover Gamma-X."
        )

    return MaterialBlock(
        model_id="IOFFE-DirectHeterointerface-EgAsEnp",
        latpar=ioffe_lattice_parameter(x_barrier),
        m_barrier=ioffe_effective_mass(x_barrier),
        pot_barrier=(
            ioffe_direct_ec_relative_to_gaas(x_barrier)
            - ioffe_direct_ec_relative_to_gaas(x_well)
        ),
        enp_barrier=ioffe_energy_gap(x_barrier) * E_CHARGE,
        m_well=ioffe_effective_mass(x_well),
        pot_well=0.0,  # [EMULATE_CONVENTION]: Ec do poço é o zero de energia.
        enp_well=ioffe_energy_gap(x_well) * E_CHARGE,
        warnings=tuple(warnings),
    )


# ============================================================================
# Modelo 2 — Ioffe Anderson Affinity / Eg_as_Enp
# ============================================================================

def model_ioffe_anderson(x_well: float, x_barrier: float) -> MaterialBlock:
    """
    Variante comparativa Ioffe + regra de Anderson.

    Difere do modelo Ioffe direto apenas na construção do pot_barrier.

    Fontes:
        - m*(x), a(x), χ(x):
            Ioffe-AlGaAs.zip -> basic.html
        - Eg(x):
            Ioffe-AlGaAs.zip -> bandstr.html
        - Anderson:
            regra de alinhamento por afinidade eletrônica;
            tratada aqui como [MODEL_CHOICE].

    O mapeamento E_np = Eg continua sendo [EMULATE_MAPPING].
    """

    validate_barrier_well(x_well, x_barrier)

    return MaterialBlock(
        model_id="IOFFE-AndersonAffinity-EgAsEnp",
        latpar=ioffe_lattice_parameter(x_barrier),
        m_barrier=ioffe_effective_mass(x_barrier),
        pot_barrier=ioffe_anderson_offset(x_well, x_barrier),
        enp_barrier=ioffe_energy_gap(x_barrier) * E_CHARGE,
        m_well=ioffe_effective_mass(x_well),
        pot_well=0.0,
        enp_well=ioffe_energy_gap(x_well) * E_CHARGE,
        warnings=(
            "O offset deste Parameter Set vem de afinidade eletrônica + "
            "regra de Anderson; não é o offset direto da heterointerface Ioffe.",
        ),
    )


# ============================================================================
# Schneider & Liu — parâmetros comuns
# ============================================================================

def schneider_liu_mass(x: float) -> float:
    """
    Massa reduzida usada nos modelos Schneider/Liu.

    EQUAÇÃO
        m*(x) = 0.067 + 0.083*x

    ORIGEM
        [DIRECT_FROM_SOURCE para o modelo two-band]
        H. Schneider & H. C. Liu (2007)
        arquivo:
            Quantum Well Infrared Photodetectors-Physics and
            Applications - Copia.pdf
        página impressa:
            p. 37
        seção:
            §3.4.4, discussão do empirical two-band model,
            após Eqs. (3.63)–(3.65).

    CONSISTÊNCIA INTERNA NO LIVRO
        p. 38, discussão da Fig. 3.6:
            Al0.33Ga0.67As/GaAs
            massa do poço = 0.067
            massa da barreira = 0.094

        A fórmula em x=0.33 fornece 0.09439.

    USO NO ONE-BAND
        Quando essa relação é usada no modelo one-band da §4.4, classificamos:
            [HYBRID_WITHIN_SAME_SOURCE]

        porque a relação em x está explicitada na seção two-band, embora seja
        consistente com os valores usados no exemplo one-band.
    """

    return (0.067 + 0.083 * x) * M0


# ============================================================================
# Modelo 3 — Schneider/Liu CBO087 One-Band
# ============================================================================

PARABOLIC_SURROGATE_ENERGY_J: Final[float] = 1.0


def model_schneider_liu_one_band(
    x_well: float,
    x_barrier: float,
) -> MaterialBlock:
    """
    Modelo Schneider/Liu one-band, tratado como parabólico.

    OFFSET
        Para GaAs/AlxGa1-xAs:
            Vb = 0.87*x  [eV]

        ORIGEM:
            Schneider & Liu (2007)
            p. 17, §3.2:
                ΔEc = (0.87 ± 0.04)*x eV
                a partir de comparação de muitos QWIPs.
            p. 73, §4.4:
                no modelo one-band de projeto, usa Vb = 0.87*x eV.

        Para poço Al_xwGa_(1-xw)As:
            Vb = 0.87*(x_barrier - x_well)

        CLASSIFICAÇÃO:
            [LINEAR_EXTENSION]
        A forma com duas ligas não é escrita literalmente no livro;
        é a diferença da mesma parametrização linear.

    MASSA
        GaAs:
            m* = 0.067 m0
            Schneider & Liu, p. 17, §3.2.

        Dependência com x:
            m*(x) = 0.067 + 0.083*x
            Schneider & Liu, p. 37, §3.4.4.
        Uso conjunto no one-band:
            [HYBRID_WITHIN_SAME_SOURCE]

    NÃO-PARABOLICIDADE
        Schneider & Liu, p. 73, §4.4:
            o modelo one-band descrito ali despreza efeitos de ordem superior,
            incluindo explicitamente band nonparabolicity.

        O limite matemático da lei do e⁻mulate:
            m(E) = m_cte * [1 + (E-V)/E_np]
        é:
            E_np -> infinito.

        O e⁻mulate não pode usar E_np = 0 para representar esse limite.

        Nesta versão:
            E_np = 1.0 J

        CLASSIFICAÇÃO:
            [EMULATE_ADAPTATION] + [NUMERICAL_SURROGATE]

        Esse valor NÃO vem do livro Schneider/Liu.

        Verificação numérica já realizada no domínio QWIP do projeto:
            Al26, barreira/poço/barreira = 50/5.2/50 nm:
            E_np = 1 J e E_np = 1e19 J produziram os mesmos níveis na
            precisão reportada pelo solver.

    LATPAR
        Schneider/Liu não fornece um ``latpar`` para este modelo.
        Para preencher o campo obrigatório do materials.data, usa-se a(x_b)
        do Ioffe:
            [EXTERNAL_SOURCE] + [EMULATE_CONVENTION]

        Em nm/nm, a auditoria do solver mostrou que isso não altera diretamente
        os autovalores.
    """

    validate_barrier_well(x_well, x_barrier)

    return MaterialBlock(
        model_id="SL-CBO087-OneBand",
        latpar=ioffe_lattice_parameter(x_barrier),
        m_barrier=schneider_liu_mass(x_barrier),
        pot_barrier=0.87 * (x_barrier - x_well),
        enp_barrier=PARABOLIC_SURROGATE_ENERGY_J,
        m_well=schneider_liu_mass(x_well),
        pot_well=0.0,
        enp_well=PARABOLIC_SURROGATE_ENERGY_J,
        warnings=(
            "Schneider/Liu one-band: latpar é externo ao modelo e vem do Ioffe "
            "somente para preencher o materials.data.",
            "E_np=1 J é surrogate numérico do limite parabólico; não é um "
            "parâmetro fornecido por Schneider/Liu.",
        ),
    )


# ============================================================================
# Schneider & Liu — empirical two-band
# ============================================================================

def schneider_liu_vc(x: float) -> float:
    """
    Borda de condução efetiva Vc(x), em eV.

    EQUAÇÃO
        Vc(x) = 0.57 * [
            1.594*x + x*(1-x)*(0.127 - 1.310*x)
        ]

    ORIGEM
        [DIRECT_FROM_SOURCE]
        Schneider & Liu (2007)
        arquivo:
            Quantum Well Infrared Photodetectors-Physics and
            Applications - Copia.pdf
        página impressa:
            p. 37
        seção:
            §3.4.4, empirical two-band model, após Eqs. (3.63)–(3.65).

    Para uma heteroestrutura x_well/x_barrier o programa usa:
        pot_barrier = Vc(x_barrier) - Vc(x_well)

    Essa subtração é:
        [DERIVED_FROM_SOURCE]
    """

    return 0.57 * (
        1.594 * x
        + x * (1.0 - x) * (0.127 - 1.310 * x)
    )


def schneider_liu_vv(x: float) -> float:
    """
    Borda de valência EFETIVA Vv(x), em eV.

    EQUAÇÃO
        Vv(x) = Vc(x)
                - 1.519 * [1 + (0.083/0.067)*x]

    ORIGEM
        [DIRECT_FROM_SOURCE]
        Schneider & Liu (2007)
        p. 37, §3.4.4, empirical two-band model.

    IMPORTANTE
        O próprio livro descreve essa quantidade como uma borda de valência
        efetiva para o modelo, e não necessariamente como a borda de valência
        física real.
    """

    return (
        schneider_liu_vc(x)
        - 1.519 * (1.0 + (0.083 / 0.067) * x)
    )


def schneider_liu_two_band_enp(x: float) -> float:
    """
    Mapeia o two-band Schneider/Liu para e_nonparab do e⁻mulate.

    FONTE DO MODELO
        Schneider & Liu (2007), p. 37, §3.4.4:

            Eq. (3.63):
                m(E) = ħ²/(2*gamma_tilde²) * (E - Vv)

            Eq. (3.64):
                gamma_tilde²*k² = (E - Vc)(E - Vv)

    DERIVAÇÃO DO PROJETO
        No edge E = Vc:

            m_ct = ħ²/(2*gamma_tilde²) * (Vc - Vv)

        então:

            m(E) = m_ct * [
                1 + (E - Vc)/(Vc - Vv)
            ]

    SOLVER
        e⁻mulate, simcore.py, linha 94 e linha 407:

            m(E) = m_ct * [1 + (E - pot)/E_np]

    IDENTIFICAÇÃO
        pot  = Vc
        E_np = Vc - Vv

    CLASSIFICAÇÃO
        [DERIVED_FROM_SOURCE] + [EMULATE_MAPPING]

    A expressão retorna E_np em eV; a conversão para J é feita na construção
    do MaterialBlock.
    """

    return schneider_liu_vc(x) - schneider_liu_vv(x)


def model_schneider_liu_two_band(
    x_well: float,
    x_barrier: float,
) -> MaterialBlock:
    """Modelo Schneider/Liu empirical two-band mapeado ao e⁻mulate."""

    validate_barrier_well(x_well, x_barrier)

    return MaterialBlock(
        model_id="SL-TwoBand-2007",
        latpar=ioffe_lattice_parameter(x_barrier),
        m_barrier=schneider_liu_mass(x_barrier),
        pot_barrier=(
            schneider_liu_vc(x_barrier)
            - schneider_liu_vc(x_well)
        ),
        enp_barrier=schneider_liu_two_band_enp(x_barrier) * E_CHARGE,
        m_well=schneider_liu_mass(x_well),
        pot_well=0.0,
        enp_well=schneider_liu_two_band_enp(x_well) * E_CHARGE,
        warnings=(
            "Schneider/Liu two-band: Vv é uma borda de valência efetiva do "
            "modelo, não necessariamente a borda de valência física.",
            "latpar é externo ao modelo e vem do Ioffe apenas para preencher "
            "o campo do materials.data.",
        ),
    )


# ============================================================================
# Vurgaftman, Meyer & Ram-Mohan (2001)
# ============================================================================

def varshni_gap(
    eg_zero: float,
    alpha_ev_per_k: float,
    beta_k: float,
    temperature_k: float,
) -> float:
    """
    Lei de Varshni usada pelo artigo.

    EQUAÇÃO
        Eg(T) = Eg(0) - alpha*T²/(T + beta)

    ORIGEM
        [DIRECT_FROM_SOURCE]
        Vurgaftman, Meyer & Ram-Mohan (2001)
        Eq. (2.13), p. 5818.
    """

    if temperature_k <= 0.0:
        raise ValueError("A temperatura deve ser positiva.")

    return eg_zero - alpha_ev_per_k * temperature_k**2 / (
        temperature_k + beta_k
    )


def vurgaftman_gaas_lattice(temperature_k: float) -> float:
    """
    Parâmetro de rede GaAs em Å.

    EQUAÇÃO
        a_GaAs(T) = 5.65325 + 3.88e-5*(T - 300)  [Å]

    ORIGEM
        [DIRECT_FROM_SOURCE]
        Vurgaftman et al. (2001)
        Table I, p. 5825.
    """

    return 5.65325 + 3.88e-5 * (temperature_k - 300.0)


def vurgaftman_alas_lattice(temperature_k: float) -> float:
    """
    Parâmetro de rede AlAs em Å.

    EQUAÇÃO
        a_AlAs(T) = 5.6611 + 2.90e-5*(T - 300)  [Å]

    ORIGEM
        [DIRECT_FROM_SOURCE]
        Vurgaftman et al. (2001)
        Table II, p. 5826.
    """

    return 5.6611 + 2.90e-5 * (temperature_k - 300.0)


def vurgaftman_lattice(x: float, temperature_k: float) -> float:
    """
    Parâmetro de rede da liga AlxGa1-xAs em Å.

    REGRA
        a(x,T) = (1-x)*a_GaAs(T) + x*a_AlAs(T)

    ORIGEM
        Vurgaftman et al. (2001), Sec. IV, p. 5837:
        os parâmetros de rede dos ternários são tratados por interpolação
        linear entre os binários.

    CLASSIFICAÇÃO
        [DIRECT_FROM_SOURCE / INTERPOLATION]
    """

    return (
        (1.0 - x) * vurgaftman_gaas_lattice(temperature_k)
        + x * vurgaftman_alas_lattice(temperature_k)
    )


def vurgaftman_eg_gamma(x: float, temperature_k: float) -> float:
    """
    Gap Gamma da liga AlxGa1-xAs, em eV.

    BINÁRIOS
        GaAs:
            Eg_Gamma(0 K) = 1.519 eV
            alpha = 0.5405 meV/K = 0.0005405 eV/K
            beta = 204 K
            Fonte: Table I, p. 5825.

        AlAs:
            Eg_Gamma(0 K) = 3.099 eV
            alpha = 0.885 meV/K = 0.000885 eV/K
            beta = 530 K
            Fonte: Table II, p. 5826.

        Dependência térmica:
            Eq. (2.13), p. 5818.

    LIGA
        Forma geral:
            Eg(AB) = (1-x)Eg(A) + xEg(B) - x(1-x)C

        Fonte:
            Eq. (4.1), Sec. IV, p. 5837.

        Para AlGaAs Gamma:
            C_Gamma(x) = -0.127 + 1.310*x  [eV]

        Fonte:
            Table XII, p. 5838.

    CLASSIFICAÇÃO
        [DIRECT_FROM_SOURCE] + aplicação da Eq. (4.1).
    """

    eg_gaas = varshni_gap(
        eg_zero=1.519,
        alpha_ev_per_k=0.0005405,
        beta_k=204.0,
        temperature_k=temperature_k,
    )

    eg_alas = varshni_gap(
        eg_zero=3.099,
        alpha_ev_per_k=0.000885,
        beta_k=530.0,
        temperature_k=temperature_k,
    )

    c_gamma = -0.127 + 1.310 * x

    return (
        (1.0 - x) * eg_gaas
        + x * eg_alas
        - x * (1.0 - x) * c_gamma
    )


def vurgaftman_delta_so(x: float) -> float:
    """
    Spin-orbit splitting Δso(x), em eV.

    ENDPOINTS
        GaAs: 0.341 eV
            Table I, p. 5825.
        AlAs: 0.280 eV
            Table II, p. 5826.

    ALLOY
        Interpolação linear usada na parametrização da liga.

    ORIGEM/CONTEXTO
        Sec. IV p. 5837 + Table XII p. 5838;
        bowing de Δso tratado como zero no conjunto adotado.

    CLASSIFICAÇÃO
        [INTERPOLATION_FROM_SOURCE]
    """

    return (1.0 - x) * 0.341 + x * 0.280


def vurgaftman_ep(x: float) -> float:
    """
    Kane energy EP(x), em eV.

    ENDPOINTS
        GaAs: EP = 28.8 eV
            Table I, p. 5825.
        AlAs: EP = 21.1 eV
            Table II, p. 5826.

    Sec. IV, p. 5837:
        para ligas, EP e F são interpolados e a massa é então recalculada
        pela Eq. (2.15).

    CLASSIFICAÇÃO
        [INTERPOLATION_FROM_SOURCE]
    """

    return (1.0 - x) * 28.8 + x * 21.1


def vurgaftman_f(x: float) -> float:
    """
    Parâmetro de bandas remotas F(x).

    ENDPOINTS
        GaAs: F = -1.94
            Table I, p. 5825.
        AlAs: F = -0.48
            Table II, p. 5826.

    Sec. IV, p. 5837:
        interpolar F na liga antes de aplicar a Eq. (2.15).

    CLASSIFICAÇÃO
        [INTERPOLATION_FROM_SOURCE]
    """

    return (1.0 - x) * (-1.94) + x * (-0.48)


def vurgaftman_effective_mass(x: float, temperature_k: float) -> float:
    """
    Massa efetiva Gamma da banda de condução, em kg.

    EQUAÇÃO
        m0/m* =
            (1 + 2F)
            + EP * (Eg + 2Δso/3) / [Eg(Eg + Δso)]

    ORIGEM
        [DIRECT_FROM_SOURCE]
        Vurgaftman et al. (2001)
        Eq. (2.15), p. 5819.

    PROCEDIMENTO PARA A LIGA
        Sec. IV, p. 5837:
            interpolar EP e F;
            calcular Eg e Δso;
            então aplicar Eq. (2.15).

    IMPORTANTE
        Portanto NÃO usamos simplesmente uma interpolação linear da massa.
    """

    eg = vurgaftman_eg_gamma(x, temperature_k)
    delta_so = vurgaftman_delta_so(x)
    ep = vurgaftman_ep(x)
    f_remote = vurgaftman_f(x)

    inverse_reduced_mass = (
        1.0
        + 2.0 * f_remote
        + ep * (eg + 2.0 * delta_so / 3.0)
        / (eg * (eg + delta_so))
    )

    return M0 / inverse_reduced_mass


def vurgaftman_ec_relative_to_gaas(
    x: float,
    temperature_k: float,
) -> float:
    """
    Borda de condução Gamma relativa ao GaAs, em eV.

    DADO DA FONTE
        Vurgaftman et al. (2001), Sec. VI-A, p. 5855:
            offset da banda de valência GaAs/AlAs ≈ 0.53 eV;
            o comportamento do offset na liga é tratado aproximadamente
            de forma linear com a composição, enquanto o CBO retém o efeito
            do bowing do gap.

    ESCOLHA/DERIVAÇÃO DO PROJETO
        Tomamos:
            Ev(x) - Ev(0) = -0.53*x

        e:
            Ec = Ev + Eg_Gamma

        então:
            Ec_Gamma(x,T) - Ec_Gamma(0,T)
                = Eg_Gamma(x,T) - Eg_Gamma(0,T) - 0.53*x

    CLASSIFICAÇÃO
        [DERIVED_FROM_SOURCE] + [MODEL_CHOICE]

    A expressão acima NÃO aparece impressa literalmente dessa forma no artigo.
    """

    return (
        vurgaftman_eg_gamma(x, temperature_k)
        - vurgaftman_eg_gamma(0.0, temperature_k)
        - 0.53 * x
    )


def vurgaftman_enp_kane_ev(x: float, temperature_k: float) -> float:
    """
    Energia de não-parabolicidade efetiva da redução Kane, em eV.

    PONTO DE PARTIDA NA FONTE
        Vurgaftman et al. (2001), Eq. (2.15), p. 5819:

            m0/m*(edge)
                = 1 + 2F
                  + EP/3 * [
                        2/Eg + 1/(Eg + Δso)
                    ]

        Essa é apenas uma forma algébrica equivalente da Eq. (2.15).

    REDUÇÃO DO PROJETO
        Para uma energia ε acima do edge, usamos a continuação Kane:

            A(ε) =
                1 + 2F
                + EP/3 * [
                    2/(Eg + ε)
                    + 1/(Eg + Δso + ε)
                ]

            m(ε) = m0 / A(ε)

        Linearizando em ε=0:

            m(ε) ≈ m(0) * [1 + α_K ε]

        com:

            α_K =
                (EP/3) * [
                    2/Eg² + 1/(Eg + Δso)²
                ] / A(0)

        O e⁻mulate usa:

            m(E) = m_ct * [1 + (E - V)/E_np]

        portanto definimos:

            E_np^(Kane) = 1 / α_K

    CLASSIFICAÇÃO
        [DERIVED_FROM_SOURCE]
        [LINEAR_APPROXIMATION]
        [EMULATE_REDUCTION]

    IMPORTANTE
        Vurgaftman et al. NÃO fornecem um parâmetro escalar chamado
        ``e_nonparab`` para o e⁻mulate. Essa grandeza é uma redução construída
        no projeto para compatibilizar o modelo de Kane com a lei linear
        implementada no solver.

    SOLVER
        simcore.py, linha 94 e linha 407:
            m(E) = m_cte * [1 + (E - V) / E_np]
    """

    eg = vurgaftman_eg_gamma(x, temperature_k)
    delta_so = vurgaftman_delta_so(x)
    ep = vurgaftman_ep(x)
    f_remote = vurgaftman_f(x)

    a_zero = (
        1.0
        + 2.0 * f_remote
        + (ep / 3.0)
        * (
            2.0 / eg
            + 1.0 / (eg + delta_so)
        )
    )

    alpha_k = (
        (ep / 3.0)
        * (
            2.0 / eg**2
            + 1.0 / (eg + delta_so)**2
        )
        / a_zero
    )

    return 1.0 / alpha_k


def model_vurgaftman(
    x_well: float,
    x_barrier: float,
    temperature_k: float,
) -> MaterialBlock:
    """
    Vurgaftman2001-Gamma-KaneLinearized.

    Este nome é deliberadamente explícito:
        - parâmetros bulk/offset têm base no artigo de 2001;
        - o tratamento de E_np é uma redução Kane linearizada para o e⁻mulate;
        - o solver continua sendo de uma única ramificação efetiva.

    Para x aproximadamente 0.42:
        Vurgaftman situa o crossover Gamma-X por volta de x~0.38 em baixa
        temperatura e ~0.39 a 300 K.

        Portanto essa composição deve ser tratada como continuação da
        ramificação Gamma em um solver reduzido, e NÃO como afirmação de que
        Gamma seja o mínimo fundamental da liga.
    """

    validate_barrier_well(x_well, x_barrier)

    warnings: list[str] = []

    if x_well >= 0.38 or x_barrier >= 0.38:
        warnings.append(
            "Vurgaftman: composição na região do crossover Gamma-X "
            "(~0.38 em baixa T; ~0.39 a 300 K). Este Parameter Set continua "
            "explicitamente a ramificação Gamma."
        )

    # O materials.data possui um único latpar.
    # Exportamos a liga da barreira como convenção do gerador.
    latpar = (
        vurgaftman_lattice(x_barrier, temperature_k)
        * ANGSTROM
    )

    return MaterialBlock(
        model_id=(
            "VUR2001-Gamma-KaneLinearized-"
            f"T{temperature_k:g}K"
        ),
        latpar=latpar,
        m_barrier=vurgaftman_effective_mass(
            x_barrier,
            temperature_k,
        ),
        pot_barrier=(
            vurgaftman_ec_relative_to_gaas(
                x_barrier,
                temperature_k,
            )
            - vurgaftman_ec_relative_to_gaas(
                x_well,
                temperature_k,
            )
        ),
        enp_barrier=(
            vurgaftman_enp_kane_ev(
                x_barrier,
                temperature_k,
            )
            * E_CHARGE
        ),
        m_well=vurgaftman_effective_mass(
            x_well,
            temperature_k,
        ),
        pot_well=0.0,
        enp_well=(
            vurgaftman_enp_kane_ev(
                x_well,
                temperature_k,
            )
            * E_CHARGE
        ),
        warnings=tuple(warnings),
    )


# ============================================================================
# Modelo 6 — GMP histórico de 07/10/2022
# ============================================================================

def model_gmp_historical(
    x_well: float,
    x_barrier: float,
) -> MaterialBlock:
    """
    Reproduz a parametrização histórica anotada por GMP em outubro de 2022.

    FONTE
        Caderno de Germano Maioli Penello.
        Arquivo disponível:
            Texto colado.txt
        Localizadores:
            07/10/2022:
                "Dados para GaAs/AlAs segundo Vurgaftman"
            10/10/2022:
                conferência dos resultados com a tese de Fernando.

    EQUAÇÕES HISTÓRICAS RECONSTRUÍDAS DAS ANOTAÇÕES
        Eg_GaAs = 1.519 eV
        Eg_AlAs = 3.099 eV

        ΔEg = 3.099 - 1.519 = 1.580 eV

        CBO(AlAs/GaAs)
            = 0.66 * ΔEg
            = 1.0428 eV

        interpolação histórica:
            Vb = 1.0428 * (x_barrier - x_well)

        massa:
            m*(x) = (0.067 + 0.083*x) m0

        não-parabolicidade histórica:
            E_np(x) = [1.519 + 1.580*x] eV

    CHECAGEM DOCUMENTAL
        Para x=0.26, a anotação de 10/10/2022 registra:
            CBO = 0.27118 eV
            m*  = 0.08858 m0
            NP  = 1.9298 eV

        As fórmulas acima fornecem, respectivamente:
            1.0428*0.26 = 0.271128 eV
            0.067 + 0.083*0.26 = 0.08858
            1.519 + 1.580*0.26 = 1.9298 eV

    CLASSIFICAÇÃO
        [HISTORICAL_PARAMETERIZATION]

    IMPORTANTE
        O nome "Vurgaftman" nesta família descreve a genealogia do caderno,
        NÃO significa que essas equações sejam a reconstrução canônica do
        artigo Vurgaftman de 2001.

    LATPAR
        O valor histórico:
            5.65315e-10 m

        aparece nos blocos históricos do materials.data.

        A origem primária exata desse valor ainda não foi localizada.
        Portanto:
            [HISTORICAL_PARAMETERIZATION]
            [SOURCE_LOCATION_NOT_CONFIRMED]

        Ele é preservado somente para reprodutibilidade histórica.
    """

    validate_barrier_well(x_well, x_barrier)

    return MaterialBlock(
        model_id="GMP-Vurgaftman-Historical-20221007",
        latpar=5.65315e-10,
        m_barrier=(0.067 + 0.083 * x_barrier) * M0,
        pot_barrier=1.0428 * (x_barrier - x_well),
        enp_barrier=(1.519 + 1.580 * x_barrier) * E_CHARGE,
        m_well=(0.067 + 0.083 * x_well) * M0,
        pot_well=0.0,
        enp_well=(1.519 + 1.580 * x_well) * E_CHARGE,
        warnings=(
            "Parametrização histórica GMP: não deve ser confundida com a "
            "reconstrução primária de Vurgaftman et al. (2001).",
            "latpar=5.65315e-10 m é preservado historicamente; a origem "
            "primária exata desse número não foi localizada.",
        ),
    )


# ============================================================================
# Renderização do materials.data
# ============================================================================

def render_materials_data_block(
    block: MaterialBlock,
    x_well: float,
    x_barrier: float,
    *,
    include_metadata_comments: bool = True,
) -> str:
    """
    Converte um MaterialBlock em texto compatível com materials.data.

    O arquivo materials.data do e⁻mulate aceita linhas iniciadas por ``#``
    como comentários. Por padrão incluímos somente metadados curtos,
    preservando o bloco legível. A proveniência detalhada permanece
    documentada no código desta versão.
    """

    barrier = material_name(x_barrier)
    well = material_name(x_well)

    section_name = (
        f"{block.model_id}-"
        f"{barrier}-{well}"
    )

    lines: list[str] = []

    if include_metadata_comments:
        lines.extend(
            [
                f"# Generated by gerador_materials_data v{__version__}",
                f"# Model: {block.model_id}",
                (
                    "# Composition: "
                    f"x_well={x_well:.6g}, "
                    f"x_barrier={x_barrier:.6g}"
                ),
            ]
        )

        for warning in block.warnings:
            lines.append(f"# WARNING: {warning}")

    lines.extend(
        [
            f"[{section_name}]",
            f"latpar = {scientific(block.latpar)}",
            "",
            f"barrier: {barrier}",
            f"m_eff_ct_barrier: {scientific(block.m_barrier)}",
            f"pot_barrier: {compact_number(block.pot_barrier)}",
            f"e_nonparab_barrier: {scientific(block.enp_barrier)}",
            "",
            f"well: {well}",
            f"m_eff_ct_well: {scientific(block.m_well)}",
            f"pot_well: {compact_number(block.pot_well)}",
            f"e_nonparab_well: {scientific(block.enp_well)}",
        ]
    )

    return "\n".join(lines)


# ============================================================================
# Menu e interface
# ============================================================================

ModelFunction = Callable[[float, float], MaterialBlock]


@dataclass(frozen=True)
class ModelMenuEntry:
    key: str
    title: str
    function: ModelFunction | None
    asks_temperature: bool = False


MODEL_MENU: Final[tuple[ModelMenuEntry, ...]] = (
    ModelMenuEntry(
        key="1",
        title="Ioffe — Direct Heterointerface / Eg_as_Enp",
        function=model_ioffe_direct,
    ),
    ModelMenuEntry(
        key="2",
        title="Ioffe — Anderson Affinity / Eg_as_Enp",
        function=model_ioffe_anderson,
    ),
    ModelMenuEntry(
        key="3",
        title="Schneider/Liu — CBO087 One-Band",
        function=model_schneider_liu_one_band,
    ),
    ModelMenuEntry(
        key="4",
        title="Schneider/Liu — Two-Band 2007",
        function=model_schneider_liu_two_band,
    ),
    ModelMenuEntry(
        key="5",
        title="Vurgaftman2001 — Gamma-KaneLinearized",
        function=None,
        asks_temperature=True,
    ),
    ModelMenuEntry(
        key="6",
        title="GMP — Vurgaftman Historical 2022-10-07",
        function=model_gmp_historical,
    ),
)


def list_models() -> None:
    """Imprime os modelos disponíveis."""

    print("\nModelos disponíveis:\n")

    for entry in MODEL_MENU:
        print(f"  {entry.key}. {entry.title}")

    print()


def get_menu_entry(choice: str) -> ModelMenuEntry:
    """Obtém uma entrada do menu pelo identificador."""

    for entry in MODEL_MENU:
        if entry.key == choice:
            return entry

    raise ValueError(f"Modelo inválido: {choice!r}")


def interactive_run() -> None:
    """Executa o fluxo interativo principal."""

    print(
        f"\ngerador_materials_data v{__version__}\n"
        "Gerador auditável para e⁻mulate / projeto QBM\n"
    )

    list_models()

    choice = input("Escolha o modelo: ").strip()
    entry = get_menu_entry(choice)

    x_barrier = read_percentage(
        "\nAl na BARREIRA (%) [ex.: 26 ou 20,7]: "
    )

    x_well = read_percentage(
        "Al no POÇO (%) [Enter = GaAs = 0%]: ",
        default=0.0,
    )

    if entry.asks_temperature:
        text = input(
            "Temperatura (K) [Enter = 300]: "
        ).strip().replace(",", ".")

        temperature_k = float(text) if text else 300.0

        block = model_vurgaftman(
            x_well=x_well,
            x_barrier=x_barrier,
            temperature_k=temperature_k,
        )
    else:
        if entry.function is None:
            raise RuntimeError("Entrada do menu sem função associada.")

        block = entry.function(x_well, x_barrier)

    print("\n" + "=" * 78)
    print("TEXTO PARA ADICIONAR AO materials.data")
    print("=" * 78 + "\n")

    print(
        render_materials_data_block(
            block,
            x_well,
            x_barrier,
        )
    )

    if block.warnings:
        print("\n" + "=" * 78)
        print("OBSERVAÇÕES")
        print("=" * 78)

        for warning in block.warnings:
            print(f"- {warning}")


# ============================================================================
# Testes internos de regressão / sanidade
# ============================================================================

def assert_close(
    actual: float,
    expected: float,
    *,
    rel_tol: float = 1e-10,
    abs_tol: float = 1e-12,
    label: str = "",
) -> None:
    """Asserção numérica com tolerância explícita."""

    if not math.isclose(
        actual,
        expected,
        rel_tol=rel_tol,
        abs_tol=abs_tol,
    ):
        raise AssertionError(
            f"{label}: obtido {actual!r}, esperado {expected!r}"
        )


def run_self_tests() -> None:
    """
    Pequena bateria de regressão sem dependências externas.

    Estes testes NÃO substituem validação científica contra a literatura ou
    contra resultados experimentais. Eles protegem contra alterações acidentais
    nas fórmulas já congeladas nesta versão.
    """

    # Ioffe direct — Al26/GaAs:
    # ΔEc = 0.79*0.26 = 0.2054 eV.
    ioffe_direct = model_ioffe_direct(0.0, 0.26)
    assert_close(
        ioffe_direct.pot_barrier,
        0.2054,
        label="Ioffe direct Al26 CBO",
    )

    # Ioffe Anderson — Al26/GaAs:
    # ΔEc = 1.1*0.26 = 0.286 eV.
    ioffe_anderson = model_ioffe_anderson(0.0, 0.26)
    assert_close(
        ioffe_anderson.pot_barrier,
        0.286,
        label="Ioffe Anderson Al26 CBO",
    )

    # Schneider/Liu one-band:
    # 0.87*0.26 = 0.2262 eV.
    sl_one = model_schneider_liu_one_band(0.0, 0.26)
    assert_close(
        sl_one.pot_barrier,
        0.2262,
        label="Schneider/Liu one-band Al26 CBO",
    )
    assert_close(
        sl_one.enp_barrier,
        1.0,
        label="Schneider/Liu parabolic surrogate",
    )

    # Schneider/Liu two-band — valor já auditado para Al26/GaAs.
    sl_two = model_schneider_liu_two_band(0.0, 0.26)
    assert_close(
        sl_two.pot_barrier,
        0.2128057152,
        rel_tol=1e-10,
        label="Schneider/Liu two-band Al26 CBO",
    )

    # GMP histórico — checagens registradas no caderno em 10/10/2022.
    gmp = model_gmp_historical(0.0, 0.26)
    assert_close(
        gmp.pot_barrier,
        0.271128,
        label="GMP Al26 CBO",
    )
    assert_close(
        gmp.m_barrier / M0,
        0.08858,
        label="GMP Al26 reduced mass",
    )
    assert_close(
        gmp.enp_barrier / E_CHARGE,
        1.9298,
        label="GMP Al26 E_np",
    )

    # Vurgaftman Gamma/Kane a 300 K — valor de regressão do conjunto auditado.
    vur = model_vurgaftman(0.0, 0.26, 300.0)
    assert_close(
        vur.pot_barrier,
        0.232047400448,
        rel_tol=1e-9,
        abs_tol=1e-12,
        label="Vurgaftman Al26 CBO at 300 K",
    )

    # Caso 3559: deve usar diferença entre x=.33 e x=.13,
    # não Ec(.33)-Ec(0).
    sl_3559 = model_schneider_liu_two_band(0.13, 0.33)
    expected = schneider_liu_vc(0.33) - schneider_liu_vc(0.13)
    assert_close(
        sl_3559.pot_barrier,
        expected,
        label="SL two-band Al33/Al13 offset",
    )

    print("Self-tests: OK")


# ============================================================================
# CLI
# ============================================================================

def build_argument_parser() -> argparse.ArgumentParser:
    """Cria a interface de linha de comando."""

    parser = argparse.ArgumentParser(
        description=(
            "Gera blocos de materiais auditáveis para o materials.data "
            "do e⁻mulate."
        )
    )

    parser.add_argument(
        "--list-models",
        action="store_true",
        help="lista os modelos disponíveis e encerra",
    )

    parser.add_argument(
        "--self-test",
        action="store_true",
        help="executa testes internos de regressão e encerra",
    )

    return parser


def main() -> None:
    """Ponto de entrada do programa."""

    parser = build_argument_parser()
    args = parser.parse_args()

    if args.list_models:
        list_models()
        return

    if args.self_test:
        run_self_tests()
        return

    try:
        interactive_run()
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(f"\nErro: {exc}") from exc


if __name__ == "__main__":
    main()
