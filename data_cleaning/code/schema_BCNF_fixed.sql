-- Flight Price & Reliability — PostgreSQL DDL (Milestone 2)
-- BCNF-fixed version: adds Route; drops derived columns duration_seconds,
--   actual_elapsed_min, cancelled; drops obstime_hhmm; adds UNIQUE/CHECK constraints.
-- Translated from the "Flight Project — CIS 5500 ER Diagram"
--   * each entity set becomes a table;
--   * each many-one relationship becomes a foreign key on the "many" side,
--     NOT NULL when that side's participation is 1..1;
--   * relationship role names (Departs from / Arrives at) become column names;
--   * each weak entity takes its owner's key plus its partial key as its primary key
--     (Segment: leg_id + segment_no; WeatherObservation: station_id + observation_date,
--     element_code);
--   * the many-many relationship Books becomes its own table, carrying its attribute;
--   * the ISA subclass DelayedFlight gets a table keyed by its superclass key.
--
-- Sources
--   D1  = Expedia flight prices (nonstop and connecting itineraries)
--   Columns crossed out in the project outline are not stored: fareBasisCode,
--   elapsedDays, baseFare, seatsRemaining, segments*EpochSeconds,
--   segmentsEquipmentDescription (D1); DepDelayMinutes, ArrDelayMinutes,
--   WheelsOff, WheelsOn (D2).
--   D2  = BTS US flight delays 2025
--   D3  = NOAA GHCN daily weather (long format)

-- ---------------------------------------------------------------------------
-- Entity: Airport
--   airport_code : D1 startingAirport/destinationAirport, D2 Origin/Dest, D3 airport_code
--   city, state  : D2 OriginCityName/OriginState, DestCityName/DestState
-- ---------------------------------------------------------------------------
CREATE TABLE airport (
    airport_code  CHAR(3)       PRIMARY KEY,
    city          VARCHAR(100),
    state         CHAR(2)
);

-- ---------------------------------------------------------------------------
-- Entity: Airline
--   airline_code : D1 segmentsAirlineCode, D2 Reporting_Airline
--   airline_name : D1 segmentsAirlineName (D2 has codes only)
-- ---------------------------------------------------------------------------
CREATE TABLE airline (
    airline_code  VARCHAR(3)    PRIMARY KEY,
    airline_name  VARCHAR(100)
);

-- ---------------------------------------------------------------------------
-- Route: one row per directed airport pair.
--   (origin_code, destination_code) -> distance_miles, so distance is stored here
--   once instead of in segment and flight_operation (which would violate BCNF).
--   distance_miles : D2 Distance (preferred), else D1 segmentsDistance
--   Load rule: insert every distinct (origin, dest) pair from D1 segments and D2.
-- ---------------------------------------------------------------------------
CREATE TABLE route (
    origin_code       CHAR(3)   NOT NULL REFERENCES airport (airport_code),
    destination_code  CHAR(3)   NOT NULL REFERENCES airport (airport_code),
    distance_miles    INTEGER   CHECK (distance_miles > 0),
    PRIMARY KEY (origin_code, destination_code),
    CHECK (origin_code <> destination_code)
);

-- ---------------------------------------------------------------------------
-- Entity: Itinerary (D1), one row per distinct legId (nonstop or connecting)
--   leg_id                : legId
--   flight_date           : flightDate
--   travel_duration       : travelDuration (ISO 8601 such as 'PT5H32M'; includes layovers)
--   total_travel_distance : totalTravelDistance
--   is_nonstop            : isNonStop
-- Origin and destination are the first segment's departure airport and the
-- last segment's arrival airport, so they are not stored twice here.
-- ---------------------------------------------------------------------------
CREATE TABLE itinerary (
    leg_id                 VARCHAR(64) PRIMARY KEY,
    flight_date            DATE       NOT NULL,
    travel_duration        INTERVAL,
    total_travel_distance  INTEGER,
    is_nonstop             BOOLEAN    NOT NULL
);

-- ---------------------------------------------------------------------------
-- Weak entity: Segment (D1), one flight within an itinerary, identified through Has
-- Key = owner key leg_id + partial key segment_no.
-- The segments* columns hold one value per segment separated by '||'; split
-- them during cleaning and number the pieces 1, 2, 3, ... as segment_no.
-- Relationships folded in (Segment side is 1..1, so NOT NULL):
--   Departs from -> origin_code, Arrives at -> destination_code, Offered by -> airline_code
--   segment_no       : position within the '||' lists
--   departure_at     : segmentsDepartureTimeRaw
--   arrival_at       : segmentsArrivalTimeRaw
--   (segmentsDurationInSeconds = arrival_at - departure_at, computed in queries;
--    segmentsDistance goes to route.distance_miles)
--   origin_code      : segmentsDepartureAirportCode
--   destination_code : segmentsArrivalAirportCode
--   airline_code     : segmentsAirlineCode (name goes to airline.airline_name)
-- ---------------------------------------------------------------------------
CREATE TABLE segment (
    leg_id            VARCHAR(64)   NOT NULL REFERENCES itinerary (leg_id) ON DELETE CASCADE,
    segment_no        SMALLINT      NOT NULL CHECK (segment_no >= 1),
    departure_at      TIMESTAMPTZ,
    arrival_at        TIMESTAMPTZ,
    origin_code       CHAR(3)       NOT NULL,
    destination_code  CHAR(3)       NOT NULL,
    airline_code      VARCHAR(3)    NOT NULL REFERENCES airline (airline_code),
    PRIMARY KEY (leg_id, segment_no),
    FOREIGN KEY (origin_code, destination_code) REFERENCES route (origin_code, destination_code),
    CHECK (arrival_at > departure_at)
);

-- ---------------------------------------------------------------------------
-- Entity: FareQuote (D1), one row per price seen for an itinerary on a search date
-- Relationship folded in: Quoted for -> leg_id (FareQuote side 1..1, so NOT NULL)
--   quote_id         : generated
--   search_date      : searchDate
--   total_fare       : totalFare
--   is_basic_economy : isBasicEconomy
--   is_refundable    : isRefundable
-- Days before departure / booking window = itinerary.flight_date - search_date,
-- computed in queries.
-- ---------------------------------------------------------------------------
CREATE TABLE fare_quote (
    quote_id          BIGSERIAL     PRIMARY KEY,
    search_date       DATE          NOT NULL,
    total_fare        NUMERIC(10,2) NOT NULL CHECK (total_fare >= 0),
    is_basic_economy  BOOLEAN       NOT NULL,
    is_refundable     BOOLEAN       NOT NULL,
    leg_id            VARCHAR(64)   NOT NULL REFERENCES itinerary (leg_id)
);

-- ---------------------------------------------------------------------------
-- Relationship: Books (one cabin assignment per quote and segment position).
-- cabin_code is quote-specific AND segment-specific (segmentsCabinCode).
-- fare_quote.quote_id determines leg_id, so storing leg_id here would violate 3NF/BCNF.
-- For each books row, the corresponding (fare_quote.leg_id, books.segment_no)
-- must exist in segment. This is a cross-table constraint: validate during load
-- (or enforce with a trigger); it cannot be a direct FK without books.leg_id.
-- ---------------------------------------------------------------------------
CREATE TABLE books (
    quote_id    BIGINT       NOT NULL REFERENCES fare_quote (quote_id) ON DELETE CASCADE,
    segment_no  SMALLINT     NOT NULL CHECK (segment_no >= 1),
    cabin_code  VARCHAR(30),
    PRIMARY KEY (quote_id, segment_no)
);

-- ---------------------------------------------------------------------------
-- Entity: FlightOperation (D2), one row per scheduled flight
-- Relationships folded in (FlightOperation side is 1..1, so NOT NULL):
--   Departs from -> origin_code, Arrives at -> destination_code, Operated by -> airline_code
--   operation_id            : generated
--   flight_date             : FlightDate
--   flight_number           : Flight_Number_Reporting_Airline
--   scheduled/actual times  : CRSDepTime, DepTime, CRSArrTime, ArrTime (local HHMM)
--   dep_delay_min, arr_delay_min : DepDelay, ArrDelay
--   taxi_out_min, taxi_in_min    : TaxiOut, TaxiIn
--   cancellation_code, diverted : CancellationCode, Diverted
--     (cancelled = cancellation_code IS NOT NULL, computed in queries)
--   scheduled_elapsed_min, air_time_min : CRSElapsedTime, AirTime
--     (ActualElapsedTime = taxi_out_min + air_time_min + taxi_in_min, computed in queries)
--   Distance goes to route.distance_miles
--   origin_code, destination_code, airline_code : Origin, Dest, Reporting_Airline
-- Delay-cause minutes live in the DelayedFlight subclass below.
-- Year/Quarter/Month/DayofMonth/DayOfWeek and DepDel15/ArrDel15 are derivable, so not stored.
-- ---------------------------------------------------------------------------
CREATE TABLE flight_operation (
    operation_id             BIGSERIAL   PRIMARY KEY,
    flight_date              DATE        NOT NULL,
    flight_number            INTEGER     NOT NULL,
    scheduled_dep_hhmm       SMALLINT    CHECK (scheduled_dep_hhmm BETWEEN 0 AND 2400),
    actual_dep_hhmm          SMALLINT    CHECK (actual_dep_hhmm BETWEEN 0 AND 2400),
    scheduled_arr_hhmm       SMALLINT    CHECK (scheduled_arr_hhmm BETWEEN 0 AND 2400),
    actual_arr_hhmm          SMALLINT    CHECK (actual_arr_hhmm BETWEEN 0 AND 2400),
    dep_delay_min            INTEGER,
    arr_delay_min            INTEGER,
    taxi_out_min             INTEGER,
    taxi_in_min              INTEGER,
    cancellation_code        CHAR(1)     CHECK (cancellation_code IN ('A', 'B', 'C', 'D')),
    diverted                 BOOLEAN     NOT NULL,
    scheduled_elapsed_min    INTEGER,
    air_time_min             INTEGER,
    origin_code              CHAR(3)     NOT NULL,
    destination_code         CHAR(3)     NOT NULL,
    airline_code             VARCHAR(3)  NOT NULL REFERENCES airline (airline_code),
    UNIQUE (flight_date, airline_code, flight_number, origin_code),
    FOREIGN KEY (origin_code, destination_code) REFERENCES route (origin_code, destination_code),
    CHECK (NOT (diverted AND cancellation_code IS NOT NULL))
);

-- ---------------------------------------------------------------------------
-- Subclass: DelayedFlight ISA FlightOperation (D2)
-- BTS reports delay causes only for flights that arrived 15+ minutes late, so
-- those attributes exist only for this subclass. Translated with the Lecture 8
-- "entity appears in both super- and subclass" approach: the subclass table holds
-- the superclass key plus its own attributes. Not covering: on-time, cancelled and
-- diverted flights have no row here. Load rule: one row per flight with ArrDel15 = 1.
--   carrier_delay_min       : CarrierDelay
--   weather_delay_min       : WeatherDelay
--   nas_delay_min           : NASDelay
--   security_delay_min      : SecurityDelay
--   late_aircraft_delay_min : LateAircraftDelay
-- ---------------------------------------------------------------------------
CREATE TABLE delayed_flight (
    operation_id             BIGINT   PRIMARY KEY
                                      REFERENCES flight_operation (operation_id) ON DELETE CASCADE,
    carrier_delay_min        INTEGER  NOT NULL CHECK (carrier_delay_min >= 0),
    weather_delay_min        INTEGER  NOT NULL CHECK (weather_delay_min >= 0),
    nas_delay_min            INTEGER  NOT NULL CHECK (nas_delay_min >= 0),
    security_delay_min       INTEGER  NOT NULL CHECK (security_delay_min >= 0),
    late_aircraft_delay_min  INTEGER  NOT NULL CHECK (late_aircraft_delay_min >= 0)
);

-- ---------------------------------------------------------------------------
-- Entity: WeatherStation (D3)
-- Relationship folded in: Maps to -> airport_code (station side 1..1, so NOT NULL)
-- One station per airport in the data, so airport_code is also a candidate key
-- (UNIQUE keeps weather joins from duplicating flight rows).
--   station_id   : id
--   airport_code : airport_code
-- ---------------------------------------------------------------------------
CREATE TABLE weather_station (
    station_id    VARCHAR(11)   PRIMARY KEY,
    airport_code  CHAR(3)       NOT NULL UNIQUE REFERENCES airport (airport_code)
);

-- ---------------------------------------------------------------------------
-- Weak entity: WeatherObservation (D3), identified through Records
-- Key = owner key station_id + partial key (observation_date, element_code)
--   station_id       : id
--   observation_date : date (YYYYMMDD)
--   element_code     : element (TMAX, TMIN, PRCP, SNOW, ...)
--   raw_value        : value (raw NOAA units, e.g. tenths of °C)
--   mflag, sflag     : mflag, sflag   (qflag is empty in every row, so not stored)
--   obstime is not stored: (station_id, element_code) -> obstime in the 2025 data,
--   a partial-key dependency that would break 2NF/BCNF.
-- ON DELETE CASCADE: a weak entity cannot exist without its owner.
-- ---------------------------------------------------------------------------
CREATE TABLE weather_observation (
    station_id        VARCHAR(11)  NOT NULL REFERENCES weather_station (station_id)
                                   ON DELETE CASCADE,
    observation_date  DATE         NOT NULL,
    element_code      VARCHAR(4)   NOT NULL,
    raw_value         INTEGER      NOT NULL,
    mflag             CHAR(1),
    sflag             CHAR(1),
    PRIMARY KEY (station_id, observation_date, element_code)
);

-- ---------------------------------------------------------------------------
-- Indexes for the page queries
-- ---------------------------------------------------------------------------
CREATE INDEX idx_itin_date        ON itinerary (flight_date, is_nonstop);
CREATE INDEX idx_seg_origin       ON segment (origin_code, airline_code);
CREATE INDEX idx_seg_dest         ON segment (destination_code);
CREATE INDEX idx_quote_leg        ON fare_quote (leg_id, search_date);
CREATE INDEX idx_op_route         ON flight_operation (origin_code, destination_code, airline_code);
CREATE INDEX idx_op_origin_date   ON flight_operation (origin_code, flight_date);
CREATE INDEX idx_op_airline_date  ON flight_operation (airline_code, flight_date);
