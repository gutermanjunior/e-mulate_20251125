# Gerador `materials.data` — v1.2.0

**Projeto:** Quantum Bragg Mirror Detectors (QBM)  
**Data:** 13/10/2026  
**Base:** `gerador_materials_data_v1_1.py` fornecido pelo usuário  
**Dependências:** Python ≥ 3.10; somente biblioteca padrão.

## Execução

Abra um terminal na pasta que contém `gerador_materials_data_v1_2.py` e execute:

```powershell
python gerador_materials_data_v1_2.py
```

O menu começa perguntando pelo **portador**:

- `1` (ou Enter): elétron, banda de condução. Mantém os seis modelos científicos/históricos da v1.1.
- `2`: buraco, banda de valência. Em seguida, escolha `1` para buraco pesado (HH) ou `2` para buraco leve (LH). Os modelos disponíveis são Ioffe direto e Ioffe+Anderson.

Depois, escolha o modelo e informe as composições da barreira e do poço em **porcentagem de alumínio**. A ausência de composição para o poço significa GaAs. O programa imprime um bloco para copiar e acrescentar ao `materials.data` do e⁻mulate.

Outros comandos:

```powershell
python gerador_materials_data_v1_2.py --list-models
python gerador_materials_data_v1_2.py --self-test
```

## Equações científicas e sua proveniência

As páginas HTML consultadas foram extraídas dos dois arquivos ZIP Ioffe entregues junto ao programa original.

| Grandeza | Equação | Fonte e classificação |
|---|---|---|
| Massa pesada (HH) | `m_hh(x) = (0.51 + 0.25*x) m0` | Ioffe-AlGaAs, `basic.html`, **DIRECT_FROM_SOURCE**. A identificação *heavy* é confirmada no GaAs, `bandstr.html`. |
| Massa leve (LH) | `m_lh(x) = (0.082 + 0.068*x) m0` | Ioffe-AlGaAs, `basic.html`, **DIRECT_FROM_SOURCE**. A identificação *light* é confirmada no GaAs, `bandstr.html`. |
| Borda de valência direta | `Ev(x)-Ev(GaAs) = -0.46*x` (eV) | Ioffe-AlGaAs, `bandstr.html`, seção **Band Discontinuities**, **DIRECT_FROM_SOURCE**. |
| Barreira de buracos (modelo direto) | `V_h = 0.46*(x_barrier-x_well)` (eV) | Diferença das bordas de valência, com inversão de sinal para buracos: **DERIVED_FROM_SOURCE + LINEAR_EXTENSION + EMULATE_MAPPING**. |
| Afinidade eletrônica | `chi(x) = 4.07 - 1.1*x` (eV) para `x < 0.45` | Ioffe-AlGaAs, `basic.html`, **DIRECT_FROM_SOURCE**. |
| Gap usado no modelo Anderson | `Eg(x) = 1.424 + 1.247*x` (eV) para `x < 0.45` | Ioffe-AlGaAs, `bandstr.html`, **DIRECT_FROM_SOURCE**. |
| Barreira de buracos (Anderson) | `V_h = (1.247 - 1.1)*(x_barrier-x_well) = 0.147*(x_barrier-x_well)` (eV) | Regra adicional de Anderson `Ev=-chi-Eg`: **MODEL_CHOICE + DERIVED_FROM_SOURCE + EMULATE_MAPPING**. **Não** equivale ao offset de valência direto do Ioffe. |
| Não parabolicidade de buracos | `e_nonparab = 1.0 J` | Surrogate para massa aproximadamente constante segundo a lei do solver: **EMULATE_ADAPTATION + NUMERICAL_SURROGATE**. **Não é um parâmetro derivado das equações de buracos do Ioffe.** |

`m0 = 9.1093837015e-31 kg`. O parâmetro de rede `latpar` continua sendo calculado pela mesma equação da v1.1 usando a composição da barreira.

## Convenção de energia para buracos

Para o elétron na condução, `pot_barrier` representa a energia da barreira acima do fundo da banda de condução do poço. Para o buraco, utiliza-se a transformação de partícula-buraco: **`V_h(camada) = Ev(poço) - Ev(camada)`**, de modo que `pot_well = 0` e a barreira de buracos seja positiva quando `x_barrier > x_well`.

Isso gera um bloco numérico no *mesmo esquema de arquivo* usado pelo e⁻mulate, mas **não transforma automaticamente o solver em um simulador multibanda da banda de valência**. Ao analisar a saída do solver, deve-se interpretar suas energias como energias positivas de confinamento dos buracos em relação ao topo de valência do poço, não como a energia absoluta da banda de valência.

O modelo usa massas HH/LH **escalares** da fonte, aplicadas à coordenada de confinamento em 1D. Não considera tensor de massa direcional, Hamiltoniano de Luttinger, mistura HH-LH, deformação/tensão de rede (*strain*), separação HH/LH por tensão ou correções térmicas. A tabela `basic.html` do Ioffe é identificada como **300 K**. Essa simplificação pode não ser adequada a estudos quantitativos de subbandas de valência de heteroestruturas reais.

## Faixa de composições

- Ioffe direto para buracos: aceita `0 <= x_well <= x_barrier <= 1`, pois a página fornecida não associa limitação explícita em `x` às fórmulas de massas HH/LH e descontinuidade de valência. Para `x >= 0.45`, emite advertência sobre a aproximação de uma banda.
- Ioffe+Anderson para buracos: exige `0 <= x_well <= x_barrier < 0.45`, pois `chi(x)` e o conjunto de gap usados nessa variante estão restritos pela fonte.
- Modelos eletrônicos: restrições físicas e validações originais da v1.1 mantidas.

## Conferência numérica — Al₀,₂₆Ga₀,₇₄As / GaAs

| Grandeza | HH | LH |
|---|---:|---:|
| Massa no poço, `m*/m0` | 0,51000 | 0,08200 |
| Massa na barreira, `m*/m0` | 0,57500 | 0,09968 |
| Barreira direta, `pot_barrier` | 0,11960 eV | 0,11960 eV |
| Barreira Anderson, `pot_barrier` | 0,03822 eV | 0,03822 eV |
| `pot_well` | 0 eV | 0 eV |
| `e_nonparab` (surrogate em ambas as camadas) | 1 J | 1 J |

A diferenciação HH/LH é feita **pela massa** no modelo escalar sem *strain*; a borda de valência adotada é comum às duas opções.

## Testes e compatibilidade

A v1.2 possui `--self-test` abrangendo os testes anteriores de elétrons, conferências das massas e offsets de buracos, heteroestrutura entre duas ligas, limite `x = 0.41`, faixa do modelo Anderson e saída textual. Os modelos originais foram mantidos sem alteração das equações.

**Limite da validação:** os testes executados cobrem o gerador, suas contas e seu formato textual. Sem os arquivos executáveis do e⁻mulate e os casos de simulação, não se demonstra nesta entrega a compatibilidade dinâmica integral nem a validade espectroscópica de subbandas HH/LH.
