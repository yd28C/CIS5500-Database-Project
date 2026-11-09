# Expedia flight prices (D1) cleaning report


## Input

- file: d1_rejects.csv
- rows read: 4,068,319
- chunk size: 250,000
- searchDate range: 2022-04-16 to 2022-10-05
- flightDate range: 2022-04-17 to 2022-11-19
- run time: 4.4 min

## Rejected rows

- bad flightDate: 0
- bad isBasicEconomy: 0
- bad isNonStop: 0
- bad isRefundable: 0
- bad legId: 0
- bad searchDate: 0
- bad segment airline code: 0
- bad segment airport code: 0
- bad segment departure/arrival time: 0
- bad starting/destination airport: 0
- bad totalFare: 0
- bad travelDuration: 0
- isNonStop disagrees with segment count: 0
- legId seen before with different segments/flightDate/isNonStop: 445
- next segment departs before previous arrives: 0
- no segments: 0
- segment arrives before it departs: 0
- segment lists have different lengths: 0
- segment origin equals destination: 0
- total rejected: 445

## Kept, but worth knowing

- CHECK books segment_no not in segment for the quote's legId (must be 0): 0
- CHECK fare_quote legId not in itinerary (must be 0): 0
- cabin codes outside coach/premium coach/business/first (kept): 0
- connections where the next segment leaves from a different airport (kept): 0
- departure epoch seconds disagree with the raw time (kept): 0
- exact duplicate rows within a chunk (dropped): 0
- first segment leaves from another airport than startingAirport (kept, metro-area search): 2,080,054
- flightDate differs from local date of first departure (kept): 532
- last segment arrives at another airport than destinationAirport (kept, metro-area search): 2,018,261
- legIds that are not 32 hex characters (kept): 0
- legIds whose totalTravelDistance differs between rows (first kept): 37,526
- legIds whose travelDuration differs between rows (first kept): 0
- rows for a legId already seen in an earlier chunk: 3,174,222
- rows in rejects file skipped (other reasons): 2,165
- searchDate after flightDate (kept): 0
- segments with no segmentsDistance: 48,702
- segmentsDurationInSeconds != arrival - departure (kept; duration is computed in queries): 0
- sum of segmentsDistance differs from totalTravelDistance by > 1 mile (kept): 12,038
- totalFare = 0 (kept): 0
- totalFare below baseFare (kept): 0
- totalFare over $5,000 (kept): 0
- totalTravelDistance <= 0 (set to null): 0
- totalTravelDistance missing (kept as null): 25,605
- travelDuration != first departure to last arrival (kept): 0
- cabin codes: {'coach': 7772515, 'first': 6613, 'premium coach': 816, 'business': 175}
- searched airport -> airport actually used (metro-area substitutes): LAX->ONT: 3,099,180, DFW->DAL: 915,303, PHL->TTN: 70,648, DEN->BJC: 10,527, MIA->PBI: 386, DFW->ATL: 203, DTW->DFW: 173, ATL->DFW: 165, PHL->BOS: 161, DFW->DTW: 157, BOS->DTW: 95, DTW->SFO: 83, OAK->IAD: 80, CLT->LAX: 75, OAK->LAX: 72, CLT->ORD: 72, ORD->DEN: 69, ATL->OAK: 61, OAK->ORD: 48, DEN->DFW: 45, BOS->SFO: 40, LGA->SFO: 40, OAK->SFO: 40, PHL->SFO: 40, ATL->SFO: 40, DFW->SFO: 40, ORD->DFW: 39, JFK->MIA: 35, LAX->ORD: 33, DEN->SAN: 32, CLT->SMF: 32, DEN->SMF: 28, CLT->SAN: 28, LGA->PHL: 27, DTW->JFK: 25, EWR->JFK: 25, LGA->BOS: 23, ATL->BOG: 10, OAK->CLE: 10, DEN->FLL: 8, DTW->SLC: 8, LAX->PHL: 8, CLT->ONT: 7, ATL->FLL: 6, LAX->MSY: 6, CLT->CUN: 6, BOS->DFW: 6, DTW->PIT: 6, LGA->SJU: 5, LGA->MYR: 5, DFW->MYR: 5, DFW->SJU: 5, LGA->CUN: 4, DFW->MIA: 4, DEN->DAL: 4, ORD->DAL: 4, BOS->PIT: 4, MIA->SEA: 2, ORD->PHX: 2, OAK->DTW: 2, MIA->BDL: 2, LGA->MIA: 2, DFW->CUN: 2, CLT->MEM: 2, LAX->SNA: 2, MIA->PHX: 1, ORD->SEA: 1, OAK->BDL: 1, MIA->DTW: 1, ORD->IAH: 1, ORD->GYE: 1, LAX->GYE: 1, LAX->IAH: 1
- airline codes with more than one name: none
- routes with more than one segmentsDistance value: 137
- days between search and flight (0..60): min 1, max 60

## Output

- new itinerary rows: 269,986
- itinerary rows in total (earlier run + this one): 5,999,650
- segment rows by segment_no: {1: 5999650, 2: 5348035, 3: 1214852, 4: 17161, 5: 32}
- fare_quote rows: 4,067,874
- books rows: 7,779,316
- airports: 122
- airlines: 12
- routes: 1,155
