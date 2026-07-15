"""

Обозначения величин (общие для UI и текстов рекомендаций).

Оформление по нормам учебника (гл. 5): индексы — Unicode суб/надстрочные символы.

"""



from __future__ import annotations



# Теплота топлива

Q_n_p = "Qᵢᵖ"  # Q^p_i — низшая теплота сгорания

Q_p_p = "Qₚᵖ"  # Q^p_p — располагаемое тепло

Q_poln = "Qполн"

Q_k = "Qк"

Q_otv = "Qотв"

Q_vod = "Qвод"

Q_v_vn = "Qв.вн"



# Топливо

c_tl = "cтл"

t_tl = "tтл"

i_tl = "iтл"



A_p = "Aᵖ"

W_r_c = "Wᵣᶜ"

W1_p = "W₁ᵖ"

W2_p = "W₂ᵖ"



# Зола и шлак

a_shl = "aшл"

a_pl = "aпл"

a_un = "aун"

C_shl = "Cшл"

C_pl = "Cпл"

C_un = "Cун"

t_shl = "tшл"

ct_shl = "(cθ)шл"



# Уходящие газы

I_ukh = "Iух"

alpha_ukh = "αух"

I_hv_0 = "Iх.в⁰"

I_gv = "Iг.в"

I_v_vn = "Iв.вн"

I_v_hv = "Iв.хв"



beta = "β"

beta_p = "β′"

beta_pp = "β″"



# Потери

q2 = "q₂"

q3 = "q₃"

q4 = "q₄"

q5 = "q₅"

q6 = "q₆"

q5_nom = "q₅ном"

q5_oxl = "q₅охл"

sum_q = "Σq"



# КПД и коэффициенты

eta_k = "ηₖ"

phi = "φ"



# Котёл

D_nom = "Dном"

D = "D"

H_neohl = "Hнеохл"



# Полезное тепло

D_pe = "Dпе"

i_pe = "iпе"

i_pv = "iпв"

D_pr = "Dпр"

i_sat = "i′"

D_pp = "Dпп"

i_pp_out = "i″пп"

i_pp_in = "i′пп"



# Расход топлива

G_phi = "Gφ"

i_phi = "iφ"

B = "B"

B_p = "Bₚ"



CO2_carb = "(CO₂)карб"

# Свойства пара (IAPWS-IF97)
T_nas = "Tнас"
h_l = "h′"
h_v = "h″"
s_l = "s′"
s_v = "s″"
v_l = "v′"
v_v = "v″"
rho_l = "ρ′"
rho_v = "ρ″"





def label(symbol: str, description: str, unit: str = "") -> str:
    """Полная подпись поля: символ — описание, единица."""
    if unit:
        return f"{symbol} — {description}, {unit}"
    return f"{symbol} — {description}"


def compact_label(symbol: str, unit: str = "") -> str:
    """Короткая подпись: только символ и единица."""
    if unit:
        return f"{symbol}, {unit}"
    return symbol


