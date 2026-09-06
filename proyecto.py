"""Estimate statutory compensation for unfair dismissal under Spanish law.

The calculation models the ordinary regime in article 56 and Transitional
Provision 11 of the Spanish Workers' Statute. This unsupported educational
project is not legal advice or a recommendation. Accuracy is not guaranteed.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


REFORM_DATE = datetime.date(2012, 2, 12)
LAST_PRE_REFORM_DATE = REFORM_DATE - datetime.timedelta(days=1)

# Both monthly rates are exact multiples of a quarter-day. Integer units keep
# the calculation independent of the caller's Decimal precision and traps.
PRE_REFORM_QUARTERS_PER_MONTH = 15  # (45 / 12) * 4
POST_REFORM_QUARTERS_PER_MONTH = 11  # (33 / 12) * 4
GENERAL_MAX_QUARTERS = 720 * 4
PRE_REFORM_MAX_QUARTERS = 1260 * 4  # 42 * 30 salary days
CALCULATION_YEAR_DAYS = 365
MIN_ANNUAL_SALARY = Decimal("0.01")
MAX_ANNUAL_SALARY = Decimal("100000000.00")  # Technical input limit, not law.
MAX_INPUT_CHARACTERS = 128


@dataclass(frozen=True)
class CompensationResult:
    """Structured result returned by :func:`calculate_compensation`.

    The component amounts already reflect the statutory caps, so they add up
    exactly to ``total_compensation`` after rounding.
    """

    months_before_reform: int
    months_after_reform: int
    compensation_days_before_reform: Decimal
    compensation_days_after_reform: Decimal
    total_compensation_days: Decimal
    compensation_before_reform: Decimal
    compensation_after_reform: Decimal
    total_compensation: Decimal
    calculation_year_days: int


def _months_of_service(start_date: datetime.date, end_date: datetime.date) -> int:
    """Return service months for an inclusive period, rounding up fractions.

    Spanish dismissal compensation is prorated by month. A service period of
    even one day counts as one month, and any days beyond complete months count
    as one additional month.
    """

    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    month_difference = (end_date.year - start_date.year) * 12
    month_difference += end_date.month - start_date.month

    # Count the inclusive remainder against the original day of the month.
    # Do not move a missing anniversary to month-end: 31 Jan to 28 Feb is one
    # prorated month, whereas 31 Jan to 1 Mar is two (CGPJ reference cases).
    return month_difference + int(end_date.day >= start_date.day)


def _split_service_months(
    start_date: datetime.date, end_date: datetime.date
) -> tuple[int, int]:
    """Split service into independent pre- and post-reform monthly periods."""

    if end_date < REFORM_DATE:
        return _months_of_service(start_date, end_date), 0

    if start_date >= REFORM_DATE:
        return 0, _months_of_service(start_date, end_date)

    months_before = _months_of_service(start_date, LAST_PRE_REFORM_DATE)
    months_after = _months_of_service(REFORM_DATE, end_date)
    return months_before, months_after


def _salary_in_cents(annual_salary: Decimal) -> int:
    """Validate the monetary input and convert it without decimal arithmetic."""

    if not isinstance(annual_salary, Decimal):
        raise TypeError("annual_salary must be a Decimal")
    if not annual_salary.is_finite() or annual_salary <= 0:
        raise ValueError("annual_salary must be a positive, finite amount")
    if not MIN_ANNUAL_SALARY <= annual_salary <= MAX_ANNUAL_SALARY:
        raise ValueError("annual_salary must be between EUR 0.01 and 100000000.00")

    parts = annual_salary.as_tuple()
    digits = list(parts.digits)
    exponent = parts.exponent
    # Accept equivalent spellings such as 36500.9000, but never silently round
    # an input with a nonzero sub-cent fraction. Decimal.normalize() would use
    # the external context, so remove trailing zeroes from the tuple instead.
    while digits[-1] == 0:
        digits.pop()
        exponent += 1
    if exponent < -2:
        raise ValueError("annual_salary must have at most two decimal places")

    coefficient = 0
    for digit in digits:
        coefficient = coefficient * 10 + digit
    return coefficient * 10 ** (exponent + 2)


def _rounded_compensation_cents(salary_cents: int, salary_day_quarters: int) -> int:
    """Round the exact positive rational amount using the HALF_UP rule."""

    denominator = CALCULATION_YEAR_DAYS * 4
    # Adding half the denominator before integer division implements HALF_UP.
    # No approximate daily salary is created, including at exact half-cents.
    return (salary_cents * salary_day_quarters + denominator // 2) // denominator


def _decimal_from_hundredths(hundredths: int) -> Decimal:
    """Construct an exact two-place Decimal, unaffected by external context."""

    return Decimal(f"{hundredths // 100}.{hundredths % 100:02d}")


def calculate_compensation(
    start_date: datetime.date,
    end_date: datetime.date,
    annual_salary: Decimal,
) -> CompensationResult:
    """Calculate a reproducible unfair-dismissal compensation estimate.

    Args:
        start_date: First day of the employment relationship.
        end_date: Last day of the employment relationship, included.
        annual_salary: Gross annual salary, including prorated extra payments;
            EUR 0.01 to 100000000.00 inclusive, with no sub-cent fraction.
            These are technical input limits, not legal salary thresholds.

    Raises:
        TypeError: If dates are not plain ``datetime.date`` objects (datetimes
            are excluded), or ``annual_salary`` is not a ``Decimal``.
        ValueError: If dates are reversed or the salary is nonfinite or outside
            the supported monetary range/precision.
    """

    if type(start_date) is not datetime.date or type(end_date) is not datetime.date:
        raise TypeError("start_date and end_date must be datetime.date values")
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    salary_cents = _salary_in_cents(annual_salary)

    months_before, months_after = _split_service_months(start_date, end_date)

    pre_quarters = min(
        months_before * PRE_REFORM_QUARTERS_PER_MONTH, PRE_REFORM_MAX_QUARTERS
    )
    raw_post_quarters = months_after * POST_REFORM_QUARTERS_PER_MONTH

    # If the pre-reform period reaches 720 days, later service cannot increase
    # the result. The pre-reform amount may nevertheless reach 42 months.
    if pre_quarters >= GENERAL_MAX_QUARTERS:
        post_quarters = 0
    else:
        post_quarters = min(raw_post_quarters, GENERAL_MAX_QUARTERS - pre_quarters)
    total_quarters = pre_quarters + post_quarters

    # Supreme Court doctrine applies the ordinary 365-day divisor even when
    # the dismissal takes place in a leap year (STS 25 February 2020).
    pre_cents = _rounded_compensation_cents(salary_cents, pre_quarters)
    total_cents = _rounded_compensation_cents(salary_cents, total_quarters)

    # Assign any one-cent component-rounding difference to the later period so
    # that the displayed components always add up to the displayed total.
    post_cents = total_cents - pre_cents

    return CompensationResult(
        months_before_reform=months_before,
        months_after_reform=months_after,
        compensation_days_before_reform=_decimal_from_hundredths(pre_quarters * 25),
        compensation_days_after_reform=_decimal_from_hundredths(post_quarters * 25),
        total_compensation_days=_decimal_from_hundredths(total_quarters * 25),
        compensation_before_reform=_decimal_from_hundredths(pre_cents),
        compensation_after_reform=_decimal_from_hundredths(post_cents),
        total_compensation=_decimal_from_hundredths(total_cents),
        calculation_year_days=CALCULATION_YEAR_DAYS,
    )


def get_date_input(message: str) -> datetime.date:
    """Read a valid date from the console."""

    while True:
        date_input = input(message).strip()
        try:
            return datetime.datetime.strptime(date_input, "%d/%m/%Y").date()
        except ValueError:
            print("Invalid date, please use dd/mm/YYYY format.")


def get_decimal_input(message: str) -> Decimal:
    """Read a salary within the calculation's supported range and precision."""

    while True:
        value_input = input(message).strip().replace(",", ".")
        if len(value_input) > MAX_INPUT_CHARACTERS:
            print(
                f"Invalid number, enter at most {MAX_INPUT_CHARACTERS} characters."
            )
            continue
        try:
            value = Decimal(value_input)
            _salary_in_cents(value)
        except InvalidOperation:
            print("Invalid number, please enter a decimal number.")
            continue
        except ValueError as error:
            print(f"Invalid number: {error}.")
            continue
        return value


def _run_console() -> None:
    """Read inputs and display a calculation with its limitations."""

    print("Unfair Dismissal Compensation Calculator")
    print("Educational project. No support or maintenance is provided.")
    print("Not legal advice or a legal recommendation. Accuracy is not guaranteed.")

    start_date = get_date_input("Contract beginning date (dd/mm/YYYY): ")
    end_date = get_date_input("Contract end date (dd/mm/YYYY): ")

    while end_date < start_date:
        print("The contract end date must be on or after the start date.")
        end_date = get_date_input("Contract end date (dd/mm/YYYY): ")

    annual_salary = get_decimal_input(
        "Gross annual salary in euros, including extra payments: "
    )
    result = calculate_compensation(start_date, end_date, annual_salary)

    print("\nSERVICE PERIODS (PRORATED BY MONTH)")
    print(
        f"Before 12 February 2012: months={result.months_before_reform}, "
        f"payable salary days={result.compensation_days_before_reform}"
    )
    print(
        f"From 12 February 2012: months={result.months_after_reform}, "
        f"payable salary days={result.compensation_days_after_reform}"
    )

    print("\nCOMPENSATION (EUR)")
    print(f"Before 12 February 2012: {result.compensation_before_reform:.2f}")
    print(f"From 12 February 2012: {result.compensation_after_reform:.2f}")
    print(f"TOTAL: {result.total_compensation:.2f}")
    print(
        f"Calculation divisor: {result.calculation_year_days} days. "
        "Educational estimate only; do not rely on it for legal or financial decisions."
    )


def main() -> int:
    """Run the console, treating end-of-input and interruption as cancellation."""

    try:
        _run_console()
    except EOFError:
        print("\nCalculation cancelled.")
        return 0
    except KeyboardInterrupt:
        print("\nCalculation cancelled.")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
