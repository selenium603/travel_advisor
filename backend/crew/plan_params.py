"""Validate typed planning output before using it with external services."""

from datetime import date

from pydantic import ValidationError

from backend.models.schemas import TravelFormDetails, TravelPlanParams


class PlanParamsError(ValueError):
    """The proposed travel parameters cannot safely drive API searches."""


def validate_plan_params(
    proposed: dict,
    form_details: TravelFormDetails | None = None,
) -> TravelPlanParams:
    """Apply explicit form values, then validate the complete API input."""
    values = dict(proposed)
    if form_details:
        values.update({
            "origin": form_details.origin,
            "departure_date": form_details.departure_date,
            "return_date": form_details.return_date,
            "duration_days": (form_details.return_date - form_details.departure_date).days,
            "travelers": form_details.travelers,
            "budget_level": form_details.budget_level,
        })
        if form_details.interests:
            values["interests"] = form_details.interests
        requirements = values.get("special_requirements") or []
        if isinstance(requirements, str):
            requirements = [requirements]
        if not isinstance(requirements, list):
            raise PlanParamsError("特殊需求必须是列表")
        values["special_requirements"] = requirements + [
            detail for detail in (form_details.traveler_details, form_details.special_requirements)
            if detail.strip()
        ]

    try:
        params = TravelPlanParams.model_validate(values)
    except ValidationError as exc:
        raise PlanParamsError(f"旅行参数格式无效：{exc}") from exc

    errors = []
    if params.departure_date < date.today():
        errors.append("出发日期不能早于今天")
    if params.return_date <= params.departure_date:
        errors.append("返程日期必须晚于出发日期")
    if params.duration_days != (params.return_date - params.departure_date).days:
        errors.append("行程天数与出发、返程日期不一致")
    placeholders = {"unknown", "none", "n/a", "待定", "未指定", "未知"}
    if any(city.casefold() in placeholders for city in params.destinations):
        errors.append("目的地必须是具体城市")
    if params.origin.casefold() in placeholders:
        errors.append("出发城市必须明确")
    if params.destination_country.casefold() in placeholders:
        errors.append("目的地国家必须明确")
    if errors:
        raise PlanParamsError("旅行参数校验失败：" + "；".join(errors))
    return params
