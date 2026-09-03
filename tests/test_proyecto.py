from datetime import date, datetime
from decimal import Decimal, Inexact, ROUND_DOWN, getcontext, localcontext
from fractions import Fraction
from random import Random

import pytest

from proyecto import calculate_compensation


ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE = Decimal("36500")


def test_contract_entirely_before_reform_uses_45_days_per_year():
    result = calculate_compensation(
        date(2010, 1, 1),
        date(2010, 12, 31),
        ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
    )

    assert result.months_before_reform == 12
    assert result.months_after_reform == 0
    assert result.total_compensation_days == Decimal("45")
    assert result.total_compensation == Decimal("4500.00")


def test_contract_entirely_after_reform_uses_33_days_per_year():
    result = calculate_compensation(
        date(2020, 1, 1),
        date(2020, 12, 31),
        ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
    )

    assert result.months_before_reform == 0
    assert result.months_after_reform == 12
    assert result.total_compensation_days == Decimal("33")
    assert result.total_compensation == Decimal("3300.00")


def test_contract_crossing_reform_calculates_both_periods_separately():
    result = calculate_compensation(
        date(2011, 2, 12),
        date(2013, 2, 11),
        ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
    )

    assert result.months_before_reform == 12
    assert result.months_after_reform == 12
    assert result.compensation_days_before_reform == Decimal("45")
    assert result.compensation_days_after_reform == Decimal("33")
    assert result.total_compensation_days == Decimal("78")
    assert result.total_compensation == Decimal("7800.00")


def test_reform_date_itself_uses_post_reform_rate():
    result = calculate_compensation(
        date(2012, 2, 12),
        date(2012, 2, 12),
        ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
    )

    assert result.months_before_reform == 0
    assert result.months_after_reform == 1
    assert result.total_compensation_days == Decimal("2.75")
    assert result.total_compensation == Decimal("275.00")


def test_leap_year_still_uses_365_day_salary_divisor():
    result = calculate_compensation(
        date(2020, 2, 1), date(2020, 2, 29), Decimal("36600")
    )

    assert result.salary_divisor == 365
    assert result.months_after_reform == 1
    assert result.total_compensation == Decimal("275.75")


def test_fraction_of_month_is_rounded_up_to_full_month():
    result = calculate_compensation(
        date(2023, 1, 1),
        date(2023, 2, 2),
        ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
    )

    assert result.months_after_reform == 2
    assert result.total_compensation_days == Decimal("5.50")
    assert result.total_compensation == Decimal("550.00")


def test_general_compensation_limit_is_720_salary_days():
    result = calculate_compensation(
        date(2012, 2, 12),
        date(2034, 2, 11),
        ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
    )

    assert result.months_after_reform == 264
    assert result.compensation_days_after_reform == Decimal("720")
    assert result.total_compensation_days == Decimal("720")
    assert result.total_compensation == Decimal("72000.00")


def test_pre_reform_amount_over_720_is_preserved_without_post_reform_increase():
    result = calculate_compensation(
        date(1995, 6, 12),
        date(2013, 2, 11),
        ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
    )

    assert result.months_before_reform == 200
    assert result.months_after_reform == 12
    assert result.compensation_days_before_reform == Decimal("750")
    assert result.compensation_days_after_reform == Decimal("0")
    assert result.total_compensation == Decimal("75000.00")


def test_pre_reform_exception_is_capped_at_42_monthly_payments():
    result = calculate_compensation(
        date(1980, 2, 12),
        date(2012, 2, 11),
        ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
    )

    assert result.months_before_reform == 384
    assert result.total_compensation_days == Decimal("1260")
    assert result.total_compensation == Decimal("126000.00")


def test_reversed_dates_are_rejected():
    with pytest.raises(ValueError, match="end_date must be on or after start_date"):
        calculate_compensation(
            date(2024, 1, 2),
            date(2024, 1, 1),
            ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
        )


def test_invalid_salaries_are_rejected():
    invalid_decimal_salaries = (
        Decimal("0"),
        Decimal("-1"),
        Decimal("Infinity"),
        Decimal("NaN"),
    )

    for salary in invalid_decimal_salaries:
        with pytest.raises(ValueError, match="positive, finite"):
            calculate_compensation(date(2024, 1, 1), date(2024, 1, 2), salary)

    with pytest.raises(TypeError, match="annual_salary must be a Decimal"):
        calculate_compensation(date(2024, 1, 1), date(2024, 1, 2), 36500)


def test_money_is_rounded_to_cents_using_half_up():
    result = calculate_compensation(
        date(2012, 2, 11), date(2012, 2, 11), Decimal("9733.82")
    )

    # The unrounded compensation is exactly EUR 100.005.
    assert result.total_compensation == Decimal("100.01")


# Synthetic inputs compared with the public CGPJ calculator on 2 September
# 2026. Its output is a non-binding reference, not a legal certification.
# https://www.poderjudicial.es/cgpj/es/Servicios/Utilidades/
# Calculo-de-indemnizaciones-por-extincion-de-contrato-de-trabajo/
@pytest.mark.parametrize(
    "start,end,pre_months,post_months,total",
    [
        (date(2023, 1, 30), date(2023, 2, 27), 0, 1, "275.00"),
        (date(2023, 1, 30), date(2023, 2, 28), 0, 1, "275.00"),
        (date(2023, 1, 30), date(2023, 3, 1), 0, 2, "550.00"),
        (date(2023, 1, 31), date(2023, 2, 27), 0, 1, "275.00"),
        (date(2023, 1, 31), date(2023, 2, 28), 0, 1, "275.00"),
        (date(2023, 1, 31), date(2023, 3, 1), 0, 2, "550.00"),
        (date(2024, 1, 31), date(2024, 2, 28), 0, 1, "275.00"),
        (date(2024, 1, 31), date(2024, 2, 29), 0, 1, "275.00"),
        (date(2024, 1, 31), date(2024, 3, 1), 0, 2, "550.00"),
        (date(2023, 1, 15), date(2024, 1, 14), 0, 12, "3300.00"),
        (date(2023, 1, 15), date(2024, 1, 15), 0, 13, "3575.00"),
        (date(2012, 2, 12), date(2012, 2, 12), 0, 1, "275.00"),
        (date(2024, 2, 29), date(2025, 3, 1), 0, 13, "3575.00"),
        (date(2024, 2, 29), date(2025, 2, 28), 0, 12, "3300.00"),
        (date(2023, 1, 15), date(2023, 2, 15), 0, 2, "550.00"),
        (date(2012, 2, 11), date(2012, 2, 12), 1, 1, "650.00"),
        (date(2023, 1, 31), date(2023, 1, 31), 0, 1, "275.00"),
    ],
    ids=[
        "jan30-feb27",
        "jan30-feb28",
        "jan30-mar01",
        "jan31-feb27",
        "jan31-feb28",
        "jan31-mar01",
        "leap-jan31-feb28",
        "leap-jan31-feb29",
        "leap-jan31-mar01",
        "anniversary-eve",
        "anniversary",
        "reform-day",
        "leap-anniversary-after",
        "leap-anniversary-eve",
        "monthly-anniversary",
        "cross-reform-one-day-each",
        "same-day",
    ],
)
def test_cgpj_reference_cases(start, end, pre_months, post_months, total):
    result = calculate_compensation(start, end, ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE)

    assert result.months_before_reform == pre_months
    assert result.months_after_reform == post_months
    assert result.total_compensation == Decimal(total)


@pytest.mark.parametrize(
    "start,end,salary,expected",
    [
        (date(2020, 1, 1), date(2026, 1, 31), "36500.90", "20075.50"),
        (date(2020, 1, 1), date(2032, 2, 29), "36500.05", "40150.06"),
        (date(1997, 8, 9), date(2009, 9, 30), "50909.71", "76364.57"),
    ],
    ids=["73-post-months", "146-post-months", "146-pre-months"],
)
def test_exact_half_cent_is_not_lost_in_daily_salary_division(
    start, end, salary, expected
):
    result = calculate_compensation(start, end, Decimal(salary))

    assert result.total_compensation == Decimal(expected)
    assert (
        result.compensation_before_reform + result.compensation_after_reform
        == result.total_compensation
    )


@pytest.mark.parametrize("trap_inexact", [False, True])
def test_decimal_context_does_not_change_results_or_leak_flags(trap_inexact):
    expected = calculate_compensation(
        date(2011, 1, 1), date(2026, 1, 31), Decimal("36500.90")
    )
    outer_context = getcontext().copy()

    with localcontext() as context:
        context.prec = 5
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = trap_inexact
        context.clear_flags()
        original_flags = context.flags.copy()
        original_traps = context.traps.copy()

        actual = calculate_compensation(
            date(2011, 1, 1), date(2026, 1, 31), Decimal("36500.90")
        )

        assert actual == expected
        assert context.prec == 5
        assert context.rounding == ROUND_DOWN
        assert context.flags == original_flags
        assert context.traps == original_traps

    assert getcontext().prec == outer_context.prec
    assert getcontext().rounding == outer_context.rounding
    assert getcontext().flags == outer_context.flags
    assert getcontext().traps == outer_context.traps


@pytest.mark.parametrize(
    "salary", ["0.001", "36500.901", "100000000.01", "1e30", "1e999999"]
)
def test_salary_outside_documented_amount_or_cent_precision_is_rejected(salary):
    with pytest.raises(ValueError):
        calculate_compensation(date(2024, 1, 1), date(2024, 1, 2), Decimal(salary))


@pytest.mark.parametrize("salary", ["-0", "-Infinity", "sNaN"])
def test_additional_non_positive_or_non_finite_salaries_are_rejected(salary):
    with pytest.raises(ValueError, match="positive, finite"):
        calculate_compensation(date(2024, 1, 1), date(2024, 1, 2), Decimal(salary))


@pytest.mark.parametrize(
    "salary,expected",
    [
        ("0.01", "0.00"),
        ("100000000.00", "753424.66"),
        ("36500.9000", "275.01"),
        ("3.6500E+4", "275.00"),
    ],
)
def test_salary_boundaries_and_insignificant_trailing_zeroes_are_accepted(
    salary, expected
):
    result = calculate_compensation(date(2024, 1, 1), date(2024, 1, 1), Decimal(salary))

    assert result.total_compensation == Decimal(expected)
    for amount in (
        result.compensation_before_reform,
        result.compensation_after_reform,
        result.total_compensation,
    ):
        assert amount.as_tuple().exponent == -2


@pytest.mark.parametrize("invalid_date", [None, "2024-01-01", datetime(2024, 1, 1)])
@pytest.mark.parametrize("argument", ["start_date", "end_date"])
def test_dates_must_be_plain_date_objects(argument, invalid_date):
    arguments = {
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 1, 2),
        "annual_salary": ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
    }
    arguments[argument] = invalid_date

    with pytest.raises(TypeError):
        calculate_compensation(**arguments)


def test_two_datetimes_are_rejected_even_when_they_are_comparable():
    with pytest.raises(TypeError):
        calculate_compensation(
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
        )


@pytest.mark.parametrize("salary", [None, True, 36500.90, "36500.90"])
def test_salary_does_not_implicitly_convert_other_types(salary):
    with pytest.raises(TypeError, match="annual_salary must be a Decimal"):
        calculate_compensation(date(2024, 1, 1), date(2024, 1, 2), salary)


@pytest.mark.parametrize(
    "start,end,days,total",
    [
        (date.min, date.min, "3.75", "375.00"),
        (date.max, date.max, "2.75", "275.00"),
        (date.min, date.max, "1260", "126000.00"),
    ],
)
def test_extreme_valid_dates_do_not_overflow(start, end, days, total):
    result = calculate_compensation(start, end, ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE)

    assert result.total_compensation_days == Decimal(days)
    assert result.total_compensation == Decimal(total)


def test_exactly_720_pre_reform_days_prevents_any_post_reform_increase():
    result = calculate_compensation(
        date(1996, 2, 12),
        date(2013, 2, 11),
        ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
    )

    assert result.months_before_reform == 192
    assert result.months_after_reform == 12
    assert result.compensation_days_before_reform == Decimal("720")
    assert result.compensation_days_after_reform == Decimal("0")
    assert result.total_compensation == Decimal("72000.00")


def test_combined_periods_are_capped_when_pre_reform_days_are_below_720():
    result = calculate_compensation(
        date(1996, 3, 12),
        date(2012, 4, 11),
        ANNUAL_SALARY_WITH_100_EURO_DAILY_RATE,
    )

    assert result.months_before_reform == 191
    assert result.months_after_reform == 2
    assert result.compensation_days_before_reform == Decimal("716.25")
    assert result.compensation_days_after_reform == Decimal("3.75")
    assert result.total_compensation_days == Decimal("720")
    assert result.total_compensation == Decimal("72000.00")


def _reference_months(start, end):
    """Count virtual anniversaries without creating or clamping invalid dates."""
    months = 1
    year, month = start.year, start.month
    while True:
        month += 1
        if month == 13:
            year, month = year + 1, 1
        if (year, month, start.day) > (end.year, end.month, end.day):
            return months
        months += 1


def _fraction_to_cents(amount):
    """Independent exact-rational oracle for positive HALF_UP amounts."""
    rounded_cents = int(amount * 100 + Fraction(1, 2))
    return Decimal(f"{rounded_cents // 100}.{rounded_cents % 100:02d}")


def test_seeded_cases_match_exact_rational_reference_and_preserve_invariants():
    random = Random(20260903)
    first_ordinal = date(1900, 1, 1).toordinal()
    last_ordinal = date(2060, 12, 31).toordinal()

    for _ in range(1000):
        start_ordinal, end_ordinal = sorted(
            [random.randint(first_ordinal, last_ordinal) for _ in range(2)]
        )
        start, end = date.fromordinal(start_ordinal), date.fromordinal(end_ordinal)
        salary_cents = random.randint(1, 10_000_000_000)
        salary = Decimal(f"{salary_cents // 100}.{salary_cents % 100:02d}")
        before = (
            _reference_months(start, min(end, date(2012, 2, 11)))
            if start < date(2012, 2, 12)
            else 0
        )
        after = (
            _reference_months(max(start, date(2012, 2, 12)), end)
            if end >= date(2012, 2, 12)
            else 0
        )
        pre_days = min(Fraction(before * 45, 12), 1260)
        total_days = (
            pre_days
            if pre_days >= 720
            else min(pre_days + Fraction(after * 33, 12), 720)
        )
        expected_pre = _fraction_to_cents(Fraction(salary) * pre_days / 365)
        expected_total = _fraction_to_cents(Fraction(salary) * total_days / 365)

        result = calculate_compensation(start, end, salary)

        assert result.months_before_reform == before
        assert result.months_after_reform == after
        assert Fraction(result.total_compensation_days) == total_days
        assert result.compensation_before_reform == expected_pre
        assert result.total_compensation == expected_total
        assert result.compensation_before_reform >= 0
        assert result.compensation_after_reform >= 0
        assert (
            result.compensation_before_reform + result.compensation_after_reform
            == result.total_compensation
        )
