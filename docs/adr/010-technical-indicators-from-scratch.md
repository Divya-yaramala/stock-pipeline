# ADR 010 - Technical Indicators Built from Scratch

## Status

Accepted

## Context

The pipeline needed SMA, RSI, Bollinger Bands, and MACD for daily stock analysis. The standard Python library for technical indicators is TA-Lib, which provides 150+ battle-tested implementations. However, TA-Lib has a well-known limitation: it wraps a C++ library and requires native compilation during installation.

## Decision

Implement all four indicators from scratch in `ingestion/technical_indicators.py` using pure Python arithmetic and numpy, rather than adding TA-Lib as a dependency.

## Reasons

- **TA-Lib requires C++ compilation — difficult in CI/CD**: TA-Lib's `pip install` regularly fails on fresh Linux runners without `libta-lib-dev` pre-installed, breaking CI pipelines and Docker builds.
- **Pure Python works everywhere without system dependencies**: The implementations use only Python built-ins and numpy, which is already in `requirements.txt` and installs cleanly on all platforms.
- **numpy already in requirements.txt**: scikit-learn (used for Isolation Forest) already pulls in numpy, so there is no new dependency weight.
- **Educational value — understand the math behind indicators**: Writing the Wilder smoothed RSI, EMA-based MACD, and standard-deviation Bollinger Bands from first principles makes the code self-documenting and easier to explain in interviews.

## Consequences

- **Slower than TA-Lib for large datasets**: The pure-Python loops are significantly slower than TA-Lib's compiled C++ kernels. For the current 5-ticker, 60-day window this is not measurable, but would matter at scale.
- **Must maintain our own implementation**: Any bugs in the indicator math are our responsibility, whereas TA-Lib implementations are community-tested.
- **No access to 150+ other TA-Lib indicators**: Adding indicators such as Stochastic Oscillator, ATR, or Williams %R would require writing them from scratch rather than calling a one-liner.
