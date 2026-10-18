"""Validated, explicitly simplified capital and exposure metrics."""

from __future__ import annotations

import math
from typing import Any


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


def calculate_metrics(data: dict[str, Any]) -> dict[str, Any]:
    """Calculate deliberately simplified, illustrative capital metrics.

    This model applies user-supplied credit risk weights, a flat operational
    charge to three-year average gross income, and a flat market charge to
    reported market exposure. Charges are converted to risk-weighted assets at
    12.5x. These are transparent teaching assumptions, not a jurisdiction's
    current rules or a regulatory compliance assessment.
    """
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    capital = _number(data.get("eligible_capital"), "eligible_capital")
    if capital < 0:
        raise ValueError("eligible_capital cannot be negative")

    exposures = data.get("credit_exposures")
    if not isinstance(exposures, list) or not exposures:
        raise ValueError("credit_exposures must be a non-empty list")
    names: set[str] = set()
    credit_rwa = 0.0
    total_credit_exposure = 0.0
    credit_breakdown: list[dict[str, float | str]] = []
    for index, item in enumerate(exposures):
        if not isinstance(item, dict):
            raise ValueError(f"credit_exposures[{index}] must be an object")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"credit_exposures[{index}].name must be a non-empty string")
        if name in names:
            raise ValueError(f"duplicate exposure name: {name}")
        names.add(name)
        amount = _number(item.get("amount"), f"{name}.amount")
        risk_weight = _number(item.get("risk_weight"), f"{name}.risk_weight")
        if amount < 0:
            raise ValueError(f"{name}.amount cannot be negative")
        if not 0.0 <= risk_weight <= 2.0:
            raise ValueError(f"{name}.risk_weight must be between 0 and 2")
        rwa = amount * risk_weight
        total_credit_exposure += amount
        credit_rwa += rwa
        credit_breakdown.append({
            "name": name, "amount": amount, "risk_weight": risk_weight, "risk_weighted_assets": rwa,
        })

    incomes = data.get("gross_income_3y")
    if not isinstance(incomes, list) or len(incomes) != 3:
        raise ValueError("gross_income_3y must contain exactly three annual values")
    numeric_incomes = [_number(value, f"gross_income_3y[{i}]") for i, value in enumerate(incomes)]
    if any(value < 0 for value in numeric_incomes):
        raise ValueError("gross_income_3y values cannot be negative")
    average_income = sum(numeric_incomes) / 3.0

    market_exposure = _number(data.get("market_exposure", 0), "market_exposure")
    if market_exposure < 0:
        raise ValueError("market_exposure cannot be negative")
    assumptions = data.get("assumptions", {})
    if not isinstance(assumptions, dict):
        raise ValueError("assumptions must be an object")
    operational_rate = _number(assumptions.get("operational_charge_rate", 0.15), "operational_charge_rate")
    market_rate = _number(assumptions.get("market_charge_rate", 0.08), "market_charge_rate")
    capital_floor = _number(assumptions.get("illustrative_total_capital_floor", 0.08), "illustrative_total_capital_floor")
    rwa_conversion = _number(assumptions.get("charge_to_rwa_multiplier", 12.5), "charge_to_rwa_multiplier")
    for label, rate in (
        ("operational_charge_rate", operational_rate),
        ("market_charge_rate", market_rate),
        ("illustrative_total_capital_floor", capital_floor),
    ):
        if not 0 <= rate <= 1:
            raise ValueError(f"{label} must be between 0 and 1")
    if rwa_conversion <= 0:
        raise ValueError("charge_to_rwa_multiplier must be positive")

    operational_charge = average_income * operational_rate
    market_charge = market_exposure * market_rate
    operational_rwa = operational_charge * rwa_conversion
    market_rwa = market_charge * rwa_conversion
    total_rwa = credit_rwa + operational_rwa + market_rwa
    capital_ratio = capital / total_rwa if total_rwa > 0 else None
    required_capital = total_rwa * capital_floor
    buffer = capital - required_capital
    total_exposure = total_credit_exposure + market_exposure

    return {
        "notice": (
            "Illustrative synthetic calculation only; not a regulatory capital "
            "determination, compliance conclusion, or current-rule implementation."
        ),
        "assumptions": {
            "credit_risk_weights": "user-supplied per exposure",
            "operational_charge": "three-year average gross income multiplied by flat illustrative rate",
            "market_charge": "reported market exposure multiplied by flat illustrative rate",
            "charge_to_rwa_multiplier": rwa_conversion,
            "illustrative_total_capital_floor": capital_floor,
            "risk_weight_bounds": [0.0, 2.0],
        },
        "credit_exposures": credit_breakdown,
        "metrics": {
            "eligible_capital": capital,
            "total_credit_exposure": total_credit_exposure,
            "credit_risk_weighted_assets": credit_rwa,
            "three_year_average_gross_income": average_income,
            "illustrative_operational_charge": operational_charge,
            "illustrative_operational_rwa": operational_rwa,
            "market_exposure": market_exposure,
            "illustrative_market_charge": market_charge,
            "illustrative_market_rwa": market_rwa,
            "illustrative_total_risk_weighted_assets": total_rwa,
            "illustrative_total_capital_ratio": capital_ratio,
            "illustrative_capital_required_at_floor": required_capital,
            "illustrative_capital_buffer": buffer,
            "illustrative_capital_buffer_basis_points": buffer / total_rwa * 10000 if total_rwa > 0 else None,
            "simple_leverage_ratio": capital / total_exposure if total_exposure > 0 else None,
        },
    }
