# Spanish Unfair Dismissal Compensation Engine

A rule-based calculation engine applied to Spanish unfair-dismissal compensation. The Python CLI models the rules before and after 12 February 2012, calendar-month proration, statutory caps and exact rounding to euro cents.

> **Educational portfolio project — no support is provided.** This is not legal advice or a legal recommendation. Results may contain errors; accuracy, completeness and currency are not guaranteed. Do not use them as the basis for legal or financial decisions without independent professional review.

The calculation is exposed through the pure `calculate_compensation()` function; the command-line interface is kept separate. This makes the legal rules testable without simulating user input.

## Quick start

The calculator has no runtime dependencies beyond Python 3.11 or later. From the repository root, run:

```bash
python proyecto.py
```

Enter the contract start date, contract end date and gross annual salary when prompted. Dates use `dd/mm/YYYY`; the salary must include prorated extra payments. Use a decimal point or comma, without thousands separators.

The accepted salary range is EUR 0.01 to EUR 100,000,000.00, with no fractions smaller than one cent. This is a technical input limit, not a legal salary threshold. The calculation function accepts `datetime.date` values (not timestamps) and a `Decimal` salary; reversed dates and invalid salaries are rejected.

## Example

This example uses a contract that crosses the 2012 reform date and a gross annual salary of EUR 36,500:

```text
$ python proyecto.py
Unfair Dismissal Compensation Calculator
Educational project. No support or maintenance is provided.
Not legal advice or a legal recommendation. Accuracy is not guaranteed.
Contract beginning date (dd/mm/YYYY): 12/02/2011
Contract end date (dd/mm/YYYY): 11/02/2013
Gross annual salary in euros, including extra payments: 36500

SERVICE PERIODS (PRORATED BY MONTH)
Before 12 February 2012: months=12, payable salary days=45.00
From 12 February 2012: months=12, payable salary days=33.00

COMPENSATION (EUR)
Before 12 February 2012: 4500.00
From 12 February 2012: 3300.00
TOTAL: 7800.00
Salary divisor: 365 days. Educational estimate only; do not rely on it for legal or financial decisions.
```

## Formula and assumptions

Let `S` be the gross annual salary, `M_pre` the service months before 12 February 2012 and `M_post` the service months from that date onwards.

| Step | Rule implemented |
| --- | --- |
| Daily salary | `S / 365`, including in leap years |
| Pre-reform service | `M_pre x (45 / 12)` salary days |
| Post-reform service | `M_post x (33 / 12)` salary days |
| General cap | 720 salary days |
| Transitional exception | If the pre-reform result alone exceeds 720 days, that result is retained and no post-reform days are added |
| Absolute cap | 42 monthly payments, represented as 1,260 salary days |

The final amount is `(S / 365) x payable_salary_days`, after applying the caps above.

Assumptions:

- The final day of employment is included.
- 12 February 2012 belongs to the post-reform period.
- Pre- and post-reform service are prorated independently.
- The inclusive month count is the difference in calendar months, plus one when the final day number is at least the start day number. Shorter months do not move the original day number: 31 January–28 February counts as one month; 31 January–1 March counts as two.
- The supplied gross annual salary is assumed to be the applicable compensation salary, including prorated extra payments. The same salary base is used for both periods.
- Salaries and results use `Decimal`. Internally, integer cents and quarter-days keep the calculation exact, with no approximate daily salary as an intermediate step. The final monetary amount is rounded once to euro cents using the `ROUND_HALF_UP` rule (an exact half-cent rounds up). Any one-cent reconciliation between displayed components is assigned to the post-reform component so that both components add up exactly to the displayed total.

## Tests

An isolated environment keeps the test tools separate from other Python projects. Create one from the repository root:

```bash
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or `source .venv/bin/activate` on macOS/Linux. Then install the pinned development dependencies and run the suite:

```bash
python -m pip install --require-hashes --requirement requirements-dev.txt
python -m pytest --quiet
```

If PowerShell blocks environment activation, use `.venv\Scripts\python.exe` instead of `python` in those two commands; no execution-policy change is needed.

The suite covers contracts entirely before and after the reform, contracts crossing the reform, the exact reform date, leap years, month-end boundaries, partial months, both statutory caps, the transitional exception above 720 days, invalid inputs and cent-level rounding. Regression cases include 31 January–28 February and exact half-cent totals.

GitHub Actions is configured to run the same suite on Python 3.11 and 3.14 for every push and pull request. It can also be started manually from the Actions tab. Test dependencies are pinned with verified package hashes; the two official GitHub Actions are pinned to full commit identifiers and use read-only repository permissions.

## Legal basis

The implemented rules were last reviewed on **3 September 2026** against the consolidated Workers' Statute published by the BOE and the CGPJ guidance listed below. The BOE page records **4 December 2025** as the latest published update to that consolidated text. This review date is not a certification of correctness or a commitment to keep the project current.

Primary and judicial sources:

- [Article 56 of the Workers' Statute](https://www.boe.es/buscar/act.php?id=BOE-A-2015-11430#a56): 33 days of salary per year, monthly proration and the general limit of 24 monthly payments.
- [Eleventh Transitional Provision of the Workers' Statute](https://www.boe.es/buscar/act.php?id=BOE-A-2015-11430#dtundecima): the 45/33-day split, the 720-day limit and the 42-month exception; paragraph 3 also preserves a separate rule for certain older contracts, excluded below.
- [Supreme Court case-law overview on monthly proration](https://www.poderjudicial.es/stfls/TRIBUNAL%20SUPREMO/ACUERDOS%20y%20ESTUDIOS%20DOCTRINALES/FICHERO/Sala%204_1.0.0.pdf): any service beyond the last complete month is treated as a complete month for this calculation.
- [CGPJ practical legal and case-law guide, v0.6, July 2026](https://www.poderjudicial.es/stfls/CGPJ/UTILIDADES/Guia_pr%C3%A1ctica_legal_y_jurisprudencial_calculo_indemnizaciones_v06_actualizada_a_julio_2026.pdf): inclusive service periods, independent monthly proration of each reform period and annual salary divided by 365, including leap years.
- [CGPJ update note, July 2026](https://www.poderjudicial.es/stfls/CGPJ/UTILIDADES/20260727_Nota_actualizacion_%20julio_2026.pdf): conversion of the statutory monthly caps to 720 and 1,260 salary days.
- [CGPJ public calculator](https://www.poderjudicial.es/cgpj/es/Servicios/Utilidades/Calculo-de-indemnizaciones-por-extincion-de-contrato-de-trabajo/): reference outputs used to check selected date boundaries. The calculator is itself indicative and non-binding; agreement with selected examples does not certify every possible case.

## Limitations

This project is a programming exercise, not a professional legal service. No support is provided, and there is no commitment to maintenance, future updates or responses to issues. Neither the code nor the documentation guarantees accurate, complete or current results. Tests check selected behaviours, not legal suitability for an individual case.

It is not legal advice, a legal recommendation or a legally binding calculation. In particular:

- It does not determine whether a dismissal is fair, unfair or void; that classification depends on facts, evidence and legal procedure.
- It calculates the statutory compensation only if compensation is the applicable outcome. It does not decide between compensation and reinstatement.
- It does not calculate back pay, interest, taxes, irregular variable remuneration, collective-agreement improvements or rules for special employment relationships.
- It excludes pre-12 February 2012 *contratos de fomento de la contratación indefinida* terminated on objective grounds where the dismissal is found unfair. The separate regime preserved by paragraph 3 of the Eleventh Transitional Provision is not implemented; the general 45/33-day formula must not be used for that case.
- It assumes one continuous employment period and a correctly determined gross annual salary.
- Employment law and case law can change. Do not rely on an output for a claim, settlement, dismissal or other legal or financial decision without independent review by a qualified professional.

The application itself does not store the dates or salary, send them over a network or require an account. Terminal logs and other software on the computer are outside its control.

## Technologies

- Python standard library: `datetime`, `dataclasses` and `decimal`, with integer arithmetic for exact rounding
- `pytest` for automated tests
- GitHub Actions for continuous integration

## Author

**Tadeo Adrián Troncoso Taraborrelli** — project design, implementation, testing and documentation.

This portfolio project was inspired by an academic exercise completed during an Erasmus course and was independently rebuilt and extended for this repository.
