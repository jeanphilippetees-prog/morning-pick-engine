# Data scoping: TSX earnings dates and SEDI insider history (scoping only)

Checked 2026-11-24. Nothing was scraped: this note comes from public product and terms pages, read once each,
plus web searches and what this repo already measured from Yahoo. Where a page could not be read, it says so.
Not legal advice; Phil should read the terms himself before any choice.

## Flag first: Yahoo's terms and this repo

Every price, dividend and earnings date in this repo comes from Yahoo Finance through yfinance, as the spec
directs. Yahoo's Terms of Service (read 2026-11-24) bar accessing or collecting data "using any automated
means" (robots, scrapers, data mining tools) without express prior permission (section 2(d)(9)). They also bar
reusing the Services for any commercial purpose (2(e)) and "high volume activity" without written consent (2(m)).
The yfinance project itself describes the data as for personal use only. The work is personal research with no
money at stake today, but the repo is public that commits derived Yahoo data (results/, prices/recent.csv
later) and runs on a schedule. **Phil should decide whether that is acceptable, or whether the nightly job
(phase 3) should move to a licensed source.**

## 1. Historical earnings dates and surprises for TSX names

| Source | Coverage | History | Access | Terms on automated access | Cost |
|---|---|---|---|---|---|
| Yahoo Finance (yfinance `get_earnings_dates`) | Measured in phase 2b: 448 of the 535 Canadian candidate names had dates (21,415 past releases), with release times; EPS estimate, reported EPS and surprise % columns where Yahoo has them (not checked for accuracy) | Up to ~60 quarters per name (RY.TO back to 2002) | Unofficial endpoint scraped by the yfinance library | Barred without permission (see the flag above) | Free |
| TMX Money (money.tmx.com) | Earnings pages for TSX/TSXV names | Not stated | Website only | Licence for "non-commercial or personal use only"; no downloading, storing or redistributing content (section 3.1). No explicit robots clause in the text read | Free to view |
| TMX Info Services, Earnings Events | "11,000 Global Equities", 20k+ events a quarter; TSX share not stated | "Most datasets since 2006" | XML via SFTP or API | Licensed product | Price on request; free trial offered |
| EODHD earnings calendar API | Global; `.TO` support not stated on the page (examples are US and Paris) | "Back to the 1990s" | REST API, JSON: report date, before/after market, estimate, actual, difference, surprise %. Queries over 10 years fail, so history must be pulled in slices | Licensed API (automated use is the product) | Paid plan (Fundamentals, All-In-One or the Corporate Events feed); tier price not checked |
| Alpha Vantage `EARNINGS` | Mostly US per third-party comparisons; TSX support not verified | Quarterly history | REST API | Licensed API | Free tier 25 requests a day per third-party sources; premium from about $50 a month |

Not checked: SEDAR+ filing dates of interim statements as an official earnings-date proxy (worth a look: it is
the regulator's record, but filing date is not the release date).

**Gap for our use:** TSX names often release after the close, and the exact time decides the reaction session.
Yahoo gives times for many names; any replacement must too (EODHD: before/after market field; TMX: "timing").

## 2. Canadian insider filings (SEDI) history

| Source | Coverage | History | Access | Terms on automated access | Cost |
|---|---|---|---|---|---|
| SEDI (sedi.ca), the regulators' system | Every insider report for Canadian reporting issuers | Electronic since June 2003; public within minutes of filing | Free public search on the website | The site serves a bot-check page (Radware) to automated clients, and its terms page could not be read by a script. Treat automated access as not permitted | Free to view |
| CSA Data Distribution Services (DDS) | SEDI insider profiles, transactions and holdings as structured feeds (from search results; the CSA page returned 403 to our reader) | Not confirmed | SFTP, machine-readable files; internal, commercial and hybrid licences | Licensed: this is the official bulk route | Price on request from the DDS team |
| LSEG insiders data | Includes Canadian insiders | From 2003 (per LSEG catalogue listing) | API and bulk | Licensed | Enterprise pricing |
| INK Research / canadianinsider.com, Avantis | Canadian insider data products | Not verified | Website, subscription | Not checked | Not checked |

## What this means for phase 5

- The only clean route to a historical insider-buy study is a licence: CSA DDS (official, likely the cheapest
  complete history) or a commercial vendor. Ask DDS for the price of the historical transactions file
  (2003-today) for internal research use.
- For earnings dates: EODHD or TMX Info Services both offer licensed access with history; both should be
  tested on a handful of TSX names (dates and release times against known releases) during a trial before
  paying. Yahoo works today but carries the terms issue above.

## Sources

- [Yahoo Terms of Service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html)
- [TMX Money Terms of Use](https://money.tmx.com/en/terms-of-use)
- [TMX Info Services: Earnings Events](https://tmxinfoservices.com/corporate-and-reference-data/global-corporate-events/earnings-events)
- [EODHD: earnings, IPO and splits calendar API](https://eodhd.com/financial-apis/calendar-upcoming-earnings-ipos-and-splits)
- [Alpha Vantage documentation](https://alphavantage.co/documentation) and [Macroption on Alpha Vantage limits](https://www.macroption.com/alpha-vantage-api-limits/)
- [SEDI](https://www.sedi.ca/sedi/SVTWelcome?locale=en_CA) and [CSA: Insider Reporting (SEDI)](https://www.securities-administrators.ca/?p=114)
- [CSA Data Distribution Services](https://www.securities-administrators.ca/?p=33446) (not readable by script)
- [LSEG insiders data](https://www.lseg.com/en/data-catalogue/company-data/ownership/insiders-data)
- [Avantis datasets](https://avantisai.com/datasets)
