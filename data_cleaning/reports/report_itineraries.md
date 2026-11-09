# Expedia flight prices (D1) cleaning report


## Input

- file: itineraries-dataset1.csv
- rows read: 82,138,753
- chunk size: 250,000
- searchDate range: 2022-04-16 to 2022-10-05
- flightDate range: 2022-04-17 to 2022-11-19
- run time: 74.8 min

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
- bad travelDuration: 142
- first segment not from startingAirport: 2,080,054
- isNonStop disagrees with segment count: 0
- last segment not to destinationAirport: 1,988,265
- legId seen before with different segments/flightDate/isNonStop: 2,006
- next segment departs before previous arrives: 17
- no segments: 0
- segment arrives before it departs: 0
- segment lists have different lengths: 0
- segment origin equals destination: 0
- total rejected: 4,070,484

## Kept, but worth knowing

- CHECK books segment_no not in segment for the quote's legId (must be 0): 0
- CHECK fare_quote legId not in itinerary (must be 0): 0
- cabin codes outside coach/premium coach/business/first (kept): 0
- connections where the next segment leaves from a different airport (kept): 0
- departure epoch seconds disagree with the raw time (kept): 0
- exact duplicate rows within a chunk (dropped): 0
- flightDate differs from local date of first departure (kept): 0
- legIds that are not 32 hex characters (kept): 0
- legIds whose totalTravelDistance differs between rows (first kept): 3
- legIds whose travelDuration differs between rows (first kept): 0
- rows for a legId already seen in an earlier chunk: 72,251,783
- searchDate after flightDate (kept): 0
- segments with no segmentsDistance: 11,540,483
- segmentsDurationInSeconds != arrival - departure (kept; duration is computed in queries): 0
- sum of segmentsDistance differs from totalTravelDistance by > 1 mile (kept): 329,795
- totalFare = 0 (kept): 0
- totalFare below baseFare (kept): 0
- totalFare over $5,000 (kept): 111
- totalTravelDistance <= 0 (set to null): 0
- totalTravelDistance missing (kept as null): 6,094,532
- travelDuration != first departure to last arrival (kept): 0
- cabin codes: {'coach': 149959160, 'first': 121163, 'premium coach': 92101, 'business': 24215}
- airline codes with more than one name: none
- routes with more than one segmentsDistance value: 389
- days between search and flight (0..60): min 1, max 60

## Output

- itinerary rows: 5,729,664
- segment rows by segment_no: {1: 5729664, 2: 5091490, 3: 1188580, 4: 17112, 5: 32}
- fare_quote rows: 78,068,269
- books rows: 142,411,783
- airports: 221
- airlines: 15
- routes: 3,115
