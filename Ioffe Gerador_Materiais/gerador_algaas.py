import sys
import getpass
from datetime import datetime

def gerar_bloco_material(x):
    if not (0.0 <= x <= 1.0):
        return "Erro: A proporção de alumínio (x) deve estar entre 0 e 1."

    # Constantes
    E_MASS = 9.1093837015e-31  # Massa do elétron em Kg
    E_CHARGE = 1.602176634e-19 # Carga do elétron em C

    # =====================================================================
    # CÁLCULOS BASEADOS NA IMAGEM
    # =====================================================================
    latpar = (5.6533 + 0.0078 * x) * 1e-10
    
    if x < 0.45:
        m_e_factor = 0.063 + 0.083 * x
        affinity_algaas = 4.07 - 1.1 * x
    else:
        m_e_factor = 0.26 
        affinity_algaas = 3.64 - 0.14 * x
        
    m_eff_ct_barrier = m_e_factor * E_MASS

    affinity_gaas = 4.07
    pot_barrier = affinity_gaas - affinity_algaas

    density = 5.32 - 1.56 * x
    debye_temp = 370 + 54 * x + 22 * (x**2)
    dielectric_static = 12.90 - 2.84 * x
    dielectric_high = 10.89 - 2.73 * x
    optical_phonon = 36.25 + 1.83 * x + 17.12 * (x**2) - 5.11 * (x**3)
    
    e_nonparab_barrier = (1.58 * x + 1.519) * E_CHARGE
    
    m_eff_ct_well = 0.063 * E_MASS 
    pot_well = 0.0
    e_nonparab_well = 1.519 * E_CHARGE

    # =====================================================================
    # METADADOS PARA O CABEÇALHO
    # =====================================================================
    data_hora_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Tenta pegar o nome do usuário do sistema operacional
    try:
        usuario = getpass.getuser()
    except Exception:
        usuario = "Desenvolvedor"
        
    nome_barreira = f"Al{x:.3g}Ga{1-x:.3g}As"

    # =====================================================================
    # FORMATAÇÃO DO OUTPUT
    # =====================================================================
    output = f"""###################################################################################################
# BLOCO DE MATERIAL: {nome_barreira} / GaAs
# =================================================================================================
# DESCRIÇÃO:     Parâmetros físicos e eletrônicos para simulação de heteroestrutura.
# FONTE:         Ioffe Institute - NSM Archive
# URL DA FONTE:  https://www.ioffe.ru/SVA/NSM/Semicond/AlGaAs/basic.html
# TEMPERATURA:   300 K
# ESTRUTURA:     Zinc Blende (Grupo de Simetria Td^2-F43m)
# GERADO POR:    {usuario} (via script gerador_algaas.py)
# DATA/HORA:     {data_hora_atual}
#
# DADOS EXTRAS DO MATERIAL ({nome_barreira}):
#  - Densidade:                       {density:.4f} g/cm³
#  - Temperatura de Debye:            {debye_temp:.2f} K
#  - Constante Dielétrica (estática): {dielectric_static:.4f}
#  - Constante Dielétrica (alta frq): {dielectric_high:.4f}
#  - Energia do fônon óptico:         {optical_phonon:.4f} meV
# =================================================================================================
[{nome_barreira}-GaAs]
latpar = {latpar:.6E}

barrier: {nome_barreira}
# Massa efetiva da barreira (m_e = {m_e_factor:.5f} m_o)
m_eff_ct_barrier: {m_eff_ct_barrier:.16e}
# Potencial da barreira (Offset de condução via Afinidade Eletrônica da tabela)
pot_barrier: {pot_barrier:.6f}
# e_nonparab_barrier: (Fallback: mantida equação do arquivo original, imagem sem gap explicito)
e_nonparab_barrier: {e_nonparab_barrier:.16e}

well: GaAs
# Massa efetiva do poço (GaAs na imagem equivale a x=0 -> 0.063 m_o)
m_eff_ct_well: {m_eff_ct_well:.16e}
pot_well: {pot_well:.1f}
# e_nonparab_well: (Fallback: mantida equação do arquivo original)
e_nonparab_well: {e_nonparab_well:.16e}
"""
    return output

def main():
    print("-" * 50)
    print("Gerador de Material AlGaAs - materials.data")
    print("-" * 50)
    
    x_val = None
    
    # Verifica se um argumento foi passado na linha de comando (ex: python script.py 0.15)
    if len(sys.argv) > 1:
        try:
            x_val = float(sys.argv[1])
            print(f"Lendo proporção de Alumínio a partir do argumento: x = {x_val}")
        except ValueError:
            print(f"[AVISO] O argumento '{sys.argv[1]}' não é um número válido. Tentando entrada manual...")
    
    # Se não houver argumento ou ele for inválido, pede o input interativamente
    if x_val is None:
        try:
            entrada = input("Digite a proporção de Alumínio (x) entre 0 e 1 (ex: 0.26): ")
            x_val = float(entrada.strip())
        except ValueError:
            print("\n[ERRO] Por favor, insira um valor numérico válido.")
            sys.exit(1)
            
    # Gera e exibe o texto
    texto_final = gerar_bloco_material(x_val)
    
    print("\n" + "="*99)
    print("COPIE O TEXTO ABAIXO PARA O SEU ARQUIVO:")
    print("="*99 + "\n")
    print(texto_final)
    print("="*99 + "\n")

if __name__ == "__main__":
    main()