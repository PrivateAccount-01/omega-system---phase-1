# Policy od07.policy/v1
RAW preserves original price/volume. EXECUTION also preserves raw basis and rejects unresolved/suspended/delisted identity or explicit blocking lifecycle. This does not certify settlement,lot size or authentic tradability; missing execution references remain blocked.

PRICE_RETURN applies share-changing comparisons and explicit fully-exercised theoretical rightsTERP. Ordinary/special cash distributions remain separate (NOT_APPLICABLE,factor1), preserving pure price return. This does not claim every vendor's special-distribution convention matches.

TOTAL_RETURN adds gross same-security ex-close reinvestment: cashD at eligible referenceQ gives quantity1+D/Q, backward price factorQ/(Q+D). Explicit EX_CLOSE_GROSS,currency,reference identity/session/knowledge required. No inferred price,tax,FX,fees or realized-return claim. VOLUME normalizes split/bonus quantities; rights/cash distributions leave traded volume unchanged under v1. Forward comparisons invert specified factors over the same event window. Backward comparisons apply only raw.trade_date<ex_date<=valid_at.

Methodological context reviewed2026-11-19: S&P DJI Index Mathematics Methodology https://www.spglobal.com/spdji/en/documents/methodologies/methodology-index-math.pdf distinguishes price return and reinvested distributions. Its index-wide reinvestment differs from this explicit single-security contract. Context only, not NSE/BSE certification or source-use permission. No exchange endpoint accessed.
