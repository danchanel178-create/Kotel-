"""
Расчётный движок теплового баланса котла.
Формулы 5-01 — 5-24 (гл. 5).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import FuelType, HeatBalanceInput, HeatBalanceResult
from .tables import q5_nominal_from_curve, slag_enthalpy

if TYPE_CHECKING:
    from ..data.providers import DataProvider
    from ..plugins.registry import PluginRegistry


class HeatBalanceCalculator:
    """Калькулятор теплового баланса. Может использоваться как модуль в составе большей системы."""

    def __init__(
        self,
        data_provider: DataProvider | None = None,
        plugin_registry: PluginRegistry | None = None,
    ) -> None:
        self._data = data_provider
        self._plugins = plugin_registry

    def calculate(self, inp: HeatBalanceInput) -> HeatBalanceResult:
        res = HeatBalanceResult()
        f, ash, flue, boiler, useful, cons = (
            inp.fuel,
            inp.ash,
            inp.flue,
            inp.boiler,
            inp.useful,
            inp.consumption,
        )

        # --- 5-03: физическое тепло топлива ---
        i_tl = f.c_tl * f.t_tl if f.include_physical_heat else 0.0
        res.i_tl = i_tl
        res.formulas_used.append("5-03")

        # --- 5-04: тепло на размораживание ---
        if f.W1_p > f.W2_p and f.W2_p < 100:
            res.delta_Q_razm = (
                3.35
                * (f.W1_p - f.W2_p)
                * (100 - f.W1_p)
                / (100 - f.W2_p)
            )
            res.formulas_used.append("5-04")

        # --- 5-02 / 5-02а: располагаемое тепло ---
        Q_v_vn_input = boiler.Q_v_vn
        if f.fuel_type == FuelType.SOLID_LIQUID:
            res.Q_p_p = f.Q_i_p + i_tl + Q_v_vn_input + res.delta_Q_razm
            res.formulas_used.append("5-02")
        else:
            res.Q_p_p = f.Q_i_p + i_tl + res.delta_Q_razm
            res.formulas_used.append("5-02а")

        if res.Q_p_p <= 0:
            res.warnings = self._build_recommendations(res, inp)
            return res

        # --- 5-05: тепло на разложение карбонатов ---
        res.Q6_carb = 40.0 * f.CO2_carb
        if f.CO2_carb > 0:
            res.formulas_used.append("5-05")

        # --- q₄: механическая неполнота (5-07, 5-09) ---
        res.C_sr = (
            ash.a_shl * ash.C_shl + ash.a_pl * ash.C_pl + ash.a_un * ash.C_un
        )
        denom_c = 100.0 - res.C_sr
        if denom_c <= 0:
            pass  # q₄ при некорректном C_ср
            denom_c = 1.0

        combustible_sum = (
            ash.a_shl * ash.C_shl + ash.a_pl * ash.C_pl + ash.a_un * ash.C_un
        )
        res.q4 = (
            combustible_sum
            / denom_c
            * 32.7e3
            * f.A_p
            / res.Q_p_p
        )
        res.formulas_used.append("5-09")

        # --- 5-08: ΔI_зл ---
        ct_zl = self._get_slag_enthalpy(ash.t_shl, ash.ct_shl)
        ct_hv = 0.26 * 30.0  # приближение (cθ)_х.в при 30°C
        res.delta_I_zl = (
            1.0  # η_ос — принимаем 1, если не задано
            * ash.a_un
            * f.A_p
            / 100.0
            * (ct_zl - ct_hv)
        )
        res.formulas_used.append("5-08")

        # --- 5-06: q₂ ---
        bracket = (
            flue.I_ukh
            - (flue.alpha_ukh - flue.beta) * flue.I_hv_0
            - flue.beta * flue.I_gv
        )
        res.q2 = (
            100.0
            / res.Q_p_p
            * bracket
            * (100.0 - res.q4)
            / 100.0
        )
        res.formulas_used.append("5-06")

        # --- q₃ ---
        res.q3 = flue.q3
        res.formulas_used.append("5-07")

        # --- 5-10: q₅ ---
        if boiler.q5_nom_override is not None:
            res.q5_nom = boiler.q5_nom_override
        else:
            curve = None
            if self._data:
                curve = self._data.get_q5_curve()
            res.q5_nom = q5_nominal_from_curve(boiler.D_nom, curve)
        if boiler.D > 0:
            res.q5 = res.q5_nom * boiler.D_nom / boiler.D
        else:
            res.q5 = res.q5_nom
            pass  # q₅ = q₅ном при D = 0
        res.formulas_used.append("5-10")

        # --- 5-12: q₆ (физическое тепло шлака) ---
        ct_shl = self._get_slag_enthalpy(ash.t_shl, ash.ct_shl)
        res.q6_shl = ash.a_shl * ct_shl * f.A_p / res.Q_p_p * 100.0
        res.formulas_used.append("5-12")

        # --- 5-13: q₅охл ---
        res.q5_oxl = 120.0 * boiler.H_neohl / res.Q_p_p * 100.0
        if boiler.H_neohl > 0:
            res.formulas_used.append("5-13")

        # --- 5-14, 5-15: суммарные потери и КПД ---
        res.sum_q = res.q2 + res.q3 + res.q4 + res.q5 + res.q6_shl + res.q5_oxl
        res.eta_k = 100.0 - res.sum_q
        res.formulas_used.extend(["5-14", "5-15"])

        if res.eta_k <= 0:
            pass  # рекомендации формируются в _build_recommendations

        # --- 5-11: коэффициент сохранения тепла ---
        denom_phi = res.eta_k + res.q5
        if denom_phi > 0:
            res.phi = 1.0 - res.q5 / denom_phi
            res.formulas_used.append("5-11")

        # --- 5-16: Q_полн (D в кг/с, i в кДж/кг → результат в кВт) ---
        spray_term = sum(d * (useful.i_pe - i_vpr) for d, i_vpr in useful.spray_flows)
        res.Q_poln = (
            useful.D_pe * (useful.i_pe - useful.i_pv)
            + useful.D_pr * (useful.i_sat - useful.i_pv)
            + spray_term
            + useful.D_pp * (useful.i_pp_out - useful.i_pp_in)
            + useful.Q_otv
            + useful.Q_vod
        )
        res.formulas_used.append("5-16")

        # --- Плагины могут скорректировать энтальпии / Q_полн ---
        if self._plugins:
            ctx = {"input": inp, "result": res}
            for plugin in self._plugins.get_hooks("before_fuel_consumption"):
                plugin.on_before_fuel_consumption(ctx)
                res.plugin_contributions[plugin.id] = ctx.get("plugin_data", {})

        # --- 5-20, 5-21 ---
        res.Q_v_vn = 0.0
        if cons.use_external_air_heat:
            res.Q_v_vn = (cons.beta_prime - cons.beta_double_prime) * (
                cons.I_v_vn - cons.I_v_hv
            )
            res.formulas_used.append("5-20")

        res.Q_phi = 0.0
        if cons.use_steam_blast:
            res.Q_phi = cons.G_phi * (cons.i_phi - 2400.0)
            res.formulas_used.append("5-21")

        # --- Q_к ---
        res.Q_k = cons.Q_k_override if cons.Q_k_override is not None else res.Q_poln

        # --- 5-19: расход топлива B ---
        denominator = f.Q_i_p * res.eta_k / 100.0 + res.Q_v_vn + res.Q_phi
        if denominator > 0 and res.Q_k > 0:
            res.B = res.Q_k / denominator
            res.formulas_used.append("5-19")
        else:
            pass  # B не рассчитан — рекомендация в _build_recommendations

        # --- 5-17: тепло избыточного воздуха «в сторону» ---
        if cons.use_excess_air_side and cons.B_rasch > 0:
            res.Q_izb = cons.B_rasch * (cons.I_v_vyh - cons.I_v_vkh) * cons.beta_v
            res.formulas_used.append("5-17")

        # --- 5-18: рециркуляция газов ---
        if cons.use_gas_recirculation:
            res.Q_rec = cons.r_g * cons.I_g
            res.formulas_used.append("5-18")

        # --- 5-22, 5-23: переход сухое → рабочее топливо ---
        res.B_corrected = res.B
        res.eta_k_corrected = res.eta_k
        if cons.use_dry_fuel_correction and cons.B_prime > 0:
            w_dry = cons.W_r_c_dry if cons.W_r_c_dry else 0.0
            if 100 - f.W_r_c != 0:
                res.B_corrected = cons.B_prime * (100 - w_dry) / (100 - f.W_r_c)
                res.formulas_used.append("5-22")
            if res.B > 0 and cons.Q_p_n_prime > 0:
                res.eta_k_corrected = (
                    cons.eta_k_prime * cons.B_prime * cons.Q_p_n_prime / (res.B * f.Q_i_p)
                )
                res.formulas_used.append("5-23")

        # --- 5-24: расчётный расход B_p ---
        res.B_p = res.B_corrected * (1.0 - res.q4 / 100.0)
        res.formulas_used.append("5-24")

        # --- 5-01: проверка баланса (информационно) ---
        res.formulas_used.append("5-01")

        res.warnings = self._build_recommendations(res, inp)
        return res

    def _build_recommendations(self, res: HeatBalanceResult, inp: HeatBalanceInput) -> list[str]:
        """Практические рекомендации по результатам расчёта."""
        from . import notation as sym

        tips: list[str] = []
        f, flue, boiler, ash = inp.fuel, inp.flue, inp.boiler, inp.ash

        if res.Q_p_p <= 0:
            return [f"Располагаемое тепло не определено — проверьте {sym.Q_n_p} и составные слагаемые."]

        if res.eta_k <= 0:
            tips.append(
                f"КПД {sym.eta_k} = {res.eta_k:.1f}% — сумма потерь превышает 100%. "
                f"Проверьте энтальпию уходящих газов, {sym.q4} и исходные данные по топливу."
            )
            return tips

        if res.q2 > 10:
            tips.append(
                f"Потери с уходящими газами {sym.q2} = {res.q2:.1f}% значительно выше нормы (обычно 4–7%). "
                f"Снизьте температуру газов ({sym.I_ukh} = {flue.I_ukh:.0f} кДж/кг), "
                f"избыток воздуха ({sym.alpha_ukh} = {flue.alpha_ukh}) или улучшите работу ВПУ."
            )
        elif res.q2 > 7:
            tips.append(
                f"{sym.q2} = {res.q2:.1f}% — на верхней границе типичного диапазона. "
                "Резерв повышения КПД — рекуперация тепла уходящих газов."
            )
        elif res.q2 < 3.5 and flue.alpha_ukh > 1.25:
            tips.append(
                f"{sym.q2} = {res.q2:.1f}% при {sym.alpha_ukh} = {flue.alpha_ukh} — "
                f"проверьте корректность энтальпий: возможно занижена {sym.I_ukh} или завышен {sym.I_hv_0}."
            )

        if res.q3 > 0.5:
            tips.append(
                f"Химическая неполнота {sym.q3} = {res.q3:.1f}% повышена. "
                "Проверьте режим горения, подачу воздуха и состояние горелок."
            )
        elif res.q3 > 0.2:
            tips.append(
                f"{sym.q3} = {res.q3:.1f}% — допустимо, но при стабилизации горения можно снизить ещё."
            )

        if res.q4 > 5:
            tips.append(
                f"Механическая неполнота {sym.q4} = {res.q4:.1f}% высока. "
                f"Проверьте помол/распыление топлива, режим топки и унос ({sym.C_un} = {ash.C_un}%, {sym.a_un} = {ash.a_un})."
            )
        elif res.q4 > 2:
            tips.append(
                f"{sym.q4} = {res.q4:.1f}% — выше типичного для промышленных котлов (0,5–1,5%). "
                "Оцените содержание горючего в шлаке и уносе."
            )

        if boiler.D_nom > 0 and boiler.D > 0:
            load_pct = boiler.D / boiler.D_nom * 100
            if load_pct < 60:
                tips.append(
                    f"Нагрузка {load_pct:.0f}% от номинала — {sym.q5} = {res.q5:.1f}% увеличена "
                    f"пропорционально {sym.D_nom}/D. При длительной работе на низкой нагрузке КПД снижается."
                )
            elif load_pct > 105:
                tips.append(
                    f"Фактическая нагрузка {load_pct:.0f}% выше номинала — "
                    f"проверьте допустимость режима и {sym.q5_oxl}."
                )

        if res.q5_oxl > 0.5:
            tips.append(
                f"Потери через неохлаждаемые поверхности {sym.q5_oxl} = {res.q5_oxl:.2f}% — "
                f"площадь {sym.H_neohl} = {boiler.H_neohl:.0f} м²."
            )

        if f.W_r_c > 20:
            tips.append(
                f"Влажность топлива {sym.W_r_c} = {f.W_r_c}% высока — "
                "снижает располагаемое тепло; при необходимости учтите тепло на размораживание/подсушку."
            )

        if flue.alpha_ukh > 1.45:
            tips.append(
                f"Избыток воздуха {sym.alpha_ukh} = {flue.alpha_ukh} завышен — "
                f"основной резерв снижения {sym.q2} без изменения конструкции котла."
            )
        elif flue.alpha_ukh < 1.1:
            tips.append(
                f"{sym.alpha_ukh} = {flue.alpha_ukh} близок к стехиометрическому — "
                f"риск неполного сгорания и роста {sym.q3}."
            )

        if res.eta_k < 82:
            tips.append(
                f"КПД {sym.eta_k} = {res.eta_k:.1f}% ниже типичного для современных котлов (88–92%). "
                f"Комплексно проанализируйте {sym.q2}, {sym.q4} и режим нагрузки."
            )
        elif res.eta_k > 94:
            tips.append(
                f"{sym.eta_k} = {res.eta_k:.1f}% подозрительно высок — "
                f"перепроверьте энтальпии, {sym.q4} и учёт физического тепла топлива."
            )

        if f.fuel_type == FuelType.SOLID_LIQUID and f.A_p > 25 and res.q6_shl > 0.3:
            tips.append(
                f"Зольность {sym.A_p} = {f.A_p}% и {sym.q6} = {res.q6_shl:.2f}% — "
                "учтите тепло физическое шлака при высокозольных топливах."
            )

        if res.B <= 0:
            tips.append(
                f"Расход топлива {sym.B} не рассчитан — задайте полезное тепло {sym.Q_poln} или {sym.Q_k} вручную."
            )

        if not tips:
            tips.append(
                f"Расчёт согласован: {sym.eta_k} = {res.eta_k:.1f}%, "
                f"{sym.sum_q} = {res.sum_q:.1f}%, {sym.q2} = {res.q2:.1f}%, {sym.q4} = {res.q4:.2f}%. "
                "Показатели в типичных пределах для данного класса котлов."
            )

        return tips

    def _get_slag_enthalpy(self, t_shl: float, override: float) -> float:
        if override > 0:
            return override
        if self._data:
            val = self._data.get_slag_enthalpy(t_shl)
            if val is not None:
                return val
        return slag_enthalpy(t_shl)
