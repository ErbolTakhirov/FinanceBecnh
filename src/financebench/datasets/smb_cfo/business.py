"""Deterministic synthetic small businesses.

Every public financial benchmark measures the same thing: reading SEC filings of large listed
companies. That is not the financial work most businesses actually do. A small business owner asks
"when do I run out of cash", "who owes me money", "can I afford this hire" — questions about a
ledger, not a 10-K.

So SMB-CFO generates real businesses with real books, and the gold answers are computed by **Python
oracles over those books** (`oracles.py`). No LLM ever produces a gold answer. That has two
consequences worth stating plainly:

1. **It is the only benchmark here that is not contaminated.** FinQA, TAT-QA and FinanceBench all
   predate every current model's training cutoff and sit in the standard scrapes. A model can score
   well on them by remembering. It cannot remember a business that was generated from a seed five
   minutes ago. A large gap between a model's FinQA score and its SMB-CFO score is itself the
   contamination signal.
2. **The gold is checkable.** An oracle is a function you can read. A benchmark whose answers were
   written by another model is a benchmark that inherits that model's mistakes.

Everything is seeded: the same seed always produces the same business, down to the last transaction.
A benchmark that regenerates differently each run cannot be reproduced, and cannot be compared with
itself.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

__all__ = [
    "CURRENCIES",
    "Business",
    "Customer",
    "Invoice",
    "Payment",
    "Supplier",
    "Transaction",
    "generate_business",
]

#: FX rates are **supplied in the data**, never assumed. A model that "knows" an exchange rate is
#: hallucinating: rates move, and a ledger's rate is whatever the books say it is.
CURRENCIES: dict[str, Decimal] = {
    "USD": Decimal("1.00"),
    "EUR": Decimal("1.09"),
    "GBP": Decimal("1.27"),
    "KZT": Decimal("0.0021"),
    "RUB": Decimal("0.0105"),
}

_REVENUE_CATEGORIES = (
    "Product sales",
    "Subscriptions",
    "Consulting",
    "Maintenance",
    "Licensing",
)
_EXPENSE_CATEGORIES = (
    "Payroll",
    "Rent",
    "Cloud hosting",
    "Marketing",
    "Software licenses",
    "Contractors",
    "Utilities",
    "Insurance",
    "Travel",
    "Cost of goods sold",
)

_COMPANY_WORDS = (
    "Northwind", "Aurora", "Beacon", "Cedar", "Delta", "Ember", "Fjord", "Granite",
    "Harbor", "Ironwood", "Juniper", "Kestrel", "Lantern", "Meridian", "Nimbus",
)  # fmt: skip
_SUFFIXES = ("Trading", "Logistics", "Systems", "Labs", "Works", "Supply", "Studio")


@dataclass(frozen=True)
class Customer:
    customer_id: str
    name: str


@dataclass(frozen=True)
class Supplier:
    supplier_id: str
    name: str


@dataclass(frozen=True)
class Invoice:
    """An invoice we issued. `amount` is **net of tax**; `tax` is stated separately.

    The gross/net split is not decoration — it is one of the traps. A model asked for "total
    receivables" that returns the net figure when the customer owes the gross is wrong by exactly
    the tax rate, and that is a real, expensive mistake.
    """

    invoice_id: str
    customer_id: str
    issue_date: date
    due_date: date
    amount: Decimal  # net of tax
    tax: Decimal
    currency: str
    paid: bool
    paid_date: date | None = None

    @property
    def gross(self) -> Decimal:
        return self.amount + self.tax


@dataclass(frozen=True)
class Payment:
    """A bill we owe a supplier."""

    payment_id: str
    supplier_id: str
    due_date: date
    amount: Decimal
    currency: str
    paid: bool
    category: str


@dataclass(frozen=True)
class Transaction:
    """One line of the bank ledger. Money in is positive, money out is negative."""

    txn_id: str
    txn_date: date
    description: str
    amount: Decimal  # signed: inflow positive, outflow negative
    currency: str
    category: str
    counterparty: str


@dataclass
class Business:
    """A small business's complete books."""

    name: str
    base_currency: str
    period_start: date
    period_end: date
    opening_balance: Decimal
    fx_rates: dict[str, Decimal]
    tax_rate: Decimal
    customers: list[Customer] = field(default_factory=list)
    suppliers: list[Supplier] = field(default_factory=list)
    invoices: list[Invoice] = field(default_factory=list)
    payables: list[Payment] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)
    monthly_budget: dict[str, Decimal] = field(default_factory=dict)
    #: The date "today" is, for questions like "what is overdue". Fixed, so the answer never drifts.
    as_of: date = date(2026, 6, 30)
    seed: int = 0

    def customer(self, customer_id: str) -> Customer | None:
        return next((c for c in self.customers if c.customer_id == customer_id), None)

    def supplier(self, supplier_id: str) -> Supplier | None:
        return next((s for s in self.suppliers if s.supplier_id == supplier_id), None)


def _money(rng: random.Random, low: int, high: int) -> Decimal:
    return Decimal(rng.randrange(low * 100, high * 100)) / 100


def generate_business(
    seed: int,
    *,
    months: int = 12,
    n_customers: int = 8,
    n_suppliers: int = 6,
    multi_currency: bool = False,
    as_of: date = date(2026, 6, 30),
) -> Business:
    """Generate one complete, self-consistent business from ``seed``.

    Self-consistency is the whole game. The ledger's closing balance must equal the opening balance
    plus every transaction — because that identity is what the oracles compute against, and a
    generator that quietly violates it produces a benchmark whose gold answers are wrong.
    ``tests/datasets/test_smb_cfo_oracles.py`` asserts the identity holds for hundreds of seeds.
    """
    rng = random.Random(seed)

    name = f"{rng.choice(_COMPANY_WORDS)} {rng.choice(_SUFFIXES)}"
    base_currency = "USD"
    period_end = as_of
    period_start = date(period_end.year - 1, period_end.month, 1) + timedelta(days=1)
    period_start = date(period_start.year, period_start.month, 1)

    fx = dict(CURRENCIES) if multi_currency else {base_currency: Decimal("1.00")}
    tax_rate = Decimal(rng.choice(["0.10", "0.12", "0.20"]))
    opening_balance = _money(rng, 20_000, 120_000)

    customers = [
        Customer(f"C{i:03d}", f"{rng.choice(_COMPANY_WORDS)} {rng.choice(_SUFFIXES)}")
        for i in range(1, n_customers + 1)
    ]
    suppliers = [
        Supplier(f"S{i:03d}", f"{rng.choice(_COMPANY_WORDS)} {rng.choice(_SUFFIXES)}")
        for i in range(1, n_suppliers + 1)
    ]

    transactions: list[Transaction] = []
    invoices: list[Invoice] = []
    payables: list[Payment] = []

    # One customer is deliberately dominant, so concentration questions have a real answer worth
    # finding rather than a uniform distribution where every answer is "about 1/n".
    anchor = customers[0]

    txn = 0
    month_starts: list[date] = []
    cursor = period_start
    for _ in range(months):
        month_starts.append(cursor)
        cursor = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )

    for month_index, month_start in enumerate(month_starts):
        # ---- revenue, growing gently with noise
        growth = Decimal(1) + Decimal(month_index) * Decimal("0.02")
        for customer in customers:
            weight = Decimal("3.0") if customer is anchor else Decimal("1.0")
            if rng.random() > 0.75 and customer is not anchor:
                continue
            net = (_money(rng, 800, 6_000) * growth * weight).quantize(Decimal("0.01"))
            tax = (net * tax_rate).quantize(Decimal("0.01"))
            currency = (
                rng.choice(list(fx)) if multi_currency and rng.random() < 0.3 else base_currency
            )
            issue = month_start + timedelta(days=rng.randrange(0, 26))
            due = issue + timedelta(days=rng.choice([14, 30, 45]))
            # Older invoices are mostly settled; recent ones often aren't. That is what makes
            # "overdue receivables" a real question rather than an arithmetic exercise.
            paid = due < as_of - timedelta(days=20) and rng.random() < 0.82
            paid_date = due + timedelta(days=rng.randrange(-5, 12)) if paid else None

            txn += 1
            invoice_id = f"INV{txn:04d}"
            invoices.append(
                Invoice(
                    invoice_id=invoice_id,
                    customer_id=customer.customer_id,
                    issue_date=issue,
                    due_date=due,
                    amount=net,
                    tax=tax,
                    currency=currency,
                    paid=paid,
                    paid_date=paid_date,
                )
            )
            if paid and paid_date is not None and paid_date <= as_of:
                transactions.append(
                    Transaction(
                        txn_id=f"T{len(transactions) + 1:04d}",
                        txn_date=paid_date,
                        description=f"Payment received — {invoice_id}",
                        amount=net + tax,
                        currency=currency,
                        category=rng.choice(_REVENUE_CATEGORIES),
                        counterparty=customer.name,
                    )
                )

        # ---- expenses: recurring first (payroll/rent every month, same amount — so a
        # missing-period question has an unambiguous answer), then variable.
        for category, low, high in (("Payroll", 12_000, 12_000), ("Rent", 3_500, 3_500)):
            transactions.append(
                Transaction(
                    txn_id=f"T{len(transactions) + 1:04d}",
                    txn_date=month_start + timedelta(days=1),
                    description=f"{category} — {month_start:%B %Y}",
                    amount=-_money(rng, low, high + 1),
                    currency=base_currency,
                    category=category,
                    counterparty="Internal",
                )
            )
        for _ in range(rng.randrange(4, 9)):
            category = rng.choice([c for c in _EXPENSE_CATEGORIES if c not in ("Payroll", "Rent")])
            supplier = rng.choice(suppliers)
            transactions.append(
                Transaction(
                    txn_id=f"T{len(transactions) + 1:04d}",
                    txn_date=month_start + timedelta(days=rng.randrange(1, 27)),
                    description=f"{category} — {supplier.name}",
                    amount=-_money(rng, 300, 4_500),
                    currency=base_currency,
                    category=category,
                    counterparty=supplier.name,
                )
            )

    # ---- unpaid supplier bills, some already overdue
    for i in range(rng.randrange(4, 10)):
        supplier = rng.choice(suppliers)
        due = as_of + timedelta(days=rng.randrange(-40, 45))
        payables.append(
            Payment(
                payment_id=f"AP{i + 1:03d}",
                supplier_id=supplier.supplier_id,
                due_date=due,
                amount=_money(rng, 500, 9_000),
                currency=base_currency,
                paid=False,
                category=rng.choice(_EXPENSE_CATEGORIES),
            )
        )

    transactions.sort(key=lambda t: (t.txn_date, t.txn_id))

    budget = {
        category: _money(rng, 2_000, 15_000) for category in rng.sample(_EXPENSE_CATEGORIES, k=5)
    }

    return Business(
        name=name,
        base_currency=base_currency,
        period_start=period_start,
        period_end=period_end,
        opening_balance=opening_balance,
        fx_rates=fx,
        tax_rate=tax_rate,
        customers=customers,
        suppliers=suppliers,
        invoices=invoices,
        payables=payables,
        transactions=transactions,
        monthly_budget=budget,
        as_of=as_of,
        seed=seed,
    )
