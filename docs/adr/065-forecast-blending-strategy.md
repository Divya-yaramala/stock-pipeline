# ADR 065 - Forecast Blending Strategy

## Status

Accepted

## Context

Single model forecasts have high variance — blending reduces it by combining complementary
strengths from Prophet and Ensemble models.

## Decision

Blend Prophet (60%) and Ensemble (40%) predictions.

## Reasons

- Prophet captures trend and seasonality well
- Ensemble captures non-linear feature interactions
- 60/40 blend favors Prophet for daily stock forecasting
- Weighted blend reduces individual model variance
- Scenario forecasts (bull/base/bear) improve decision-making

## Consequences

- Blend weights must be tuned per ticker/market condition
- Combined model harder to explain than single model
- Future: dynamic weight adjustment based on recent accuracy
