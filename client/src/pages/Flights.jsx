import React, { useState } from 'react';
import { useData, money, number, pct } from '../api';
import { Status, Card, Title, Select } from '../components';

function Bars({ data }) {
  if (!data?.length) return <p className="status">No fare trends available.</p>;
  const max = Math.max(...data.map(d => Number(d.avg_price)), 1);
  return <div className="bars">{data.map(d => <div className="bar-column" key={d.booking_window}><b>{money(d.avg_price)}</b><div className="bar-track"><div className="bar" style={{ height: `${Number(d.avg_price) / max * 100}%` }} /></div><span>{d.booking_window}</span></div>)}</div>;
}

function flightTime(value) {
  if (value == null) return '—';
  const hhmm = String(value).padStart(4, '0');
  return `${hhmm.slice(0, 2)}:${hhmm.slice(2)}`;
}

export default function Flights({ airports }) {
  const [origin, setOrigin] = useState('PHL');
  const [destination, setDestination] = useState('LAX');
  const [date, setDate] = useState('2025-05-15');
  const [departureStart, setDepartureStart] = useState('');
  const [departureEnd, setDepartureEnd] = useState('');
  const [ticketType, setTicketType] = useState('any');
  const [sort, setSort] = useState('departure');
  const [search, setSearch] = useState('');
  const results = useData(search);
  const trends = useData(search ? '/flights/booking-trends' : null);
  const options = airports.data || [];
  const rows = [...(results.data || [])].sort((a, b) => {
    if (sort === 'price') return (a.median_fare ?? Infinity) - (b.median_fare ?? Infinity);
    if (sort === 'duration') return (a.scheduled_elapsed_min ?? Infinity) - (b.scheduled_elapsed_min ?? Infinity);
    return (a.scheduled_dep_hhmm ?? Infinity) - (b.scheduled_dep_hhmm ?? Infinity);
  });
  function submit(e) {
    e.preventDefault();
    const params = new URLSearchParams({ origin, destination, date, ticketType });
    if (departureStart) params.set('departureStart', departureStart);
    if (departureEnd) params.set('departureEnd', departureEnd);
    setSearch(`/flights/search?${params}`);
  }
  return <>
    <Title title="Find flights" description="Compare flight times, reliability and price history." />
    <Card className="search-card">
      <div className="section-heading"><div><h2>Where are you headed?</h2></div></div>
      <form id="flight-search" className="search-grid" onSubmit={submit}>
        <Select label="From" value={origin} onChange={setOrigin}>{options.length ? options.map(a => <option key={a.airport_code} value={a.airport_code}>{a.airport_code} · {a.city || a.airport_code}</option>) : <option value="PHL">PHL · Philadelphia</option>}</Select>
        <button type="button" className="swap" aria-label="Swap airports" onClick={() => { setOrigin(destination); setDestination(origin); }}>⇄</button>
        <Select label="To" value={destination} onChange={setDestination}>{options.length ? options.map(a => <option key={a.airport_code} value={a.airport_code}>{a.airport_code} · {a.city || a.airport_code}</option>) : <option value="LAX">LAX · Los Angeles</option>}</Select>
        <label><span>Travel date</span><input type="date" min="2025-01-01" max="2025-12-31" required value={date} onChange={e => setDate(e.target.value)} /></label>
        <button className="primary">Search flights</button>
      </form>
    </Card>
    <div className="flight-layout">
      <Card>
        <div className="section-heading"><div><h2>Flight results</h2><p>{search ? `${rows.length} flights found` : 'Choose your route and travel date to begin.'}</p></div><span className="section-icon">✈</span></div>
        <div className="filters">
          <label><span>Departure from</span><input type="time" value={departureStart} onChange={e => setDepartureStart(e.target.value)} /></label>
          <label><span>Departure before</span><input type="time" value={departureEnd} onChange={e => setDepartureEnd(e.target.value)} /></label>
          <Select label="Ticket type" value={ticketType} onChange={setTicketType}><option value="any">Any ticket</option><option value="basic">Basic economy</option><option value="refundable">Refundable</option></Select>
          <Select label="Sort by" value={sort} onChange={setSort}><option value="departure">Departure time</option><option value="duration">Shortest duration</option><option value="price">2022 median fare</option></Select>
          <span className="filter-note">Filters apply when you search. Time is based on local time.</span>
        </div>
        {search && <Status state={results}>{rows.length ? <><div className="table-scroll"><table><thead><tr><th>2025 flight</th><th>Departure</th><th>Arrival</th><th>Duration</th><th>Route delay / cancel</th><th>2022 fare reference</th></tr></thead><tbody>{rows.map(r => <tr key={r.operation_id}><td><b>{r.airline_name || r.airline_code}</b><br />{r.airline_code} {r.flight_number}</td><td>{flightTime(r.scheduled_dep_hhmm)}</td><td>{flightTime(r.scheduled_arr_hhmm)}</td><td>{r.scheduled_elapsed_min == null ? '—' : `${r.scheduled_elapsed_min} min`}</td><td>{pct(r.delay_rate)} / {pct(r.cancellation_rate)}<br /><small>{number(r.monthly_flights)} flights</small></td><td>{r.quote_count ? <><b className="price">{money(r.median_fare)} median</b><br /><small>{money(r.min_fare)}–{money(r.max_fare)} · {number(r.quote_count)} quotes</small></> : 'No matching fares'}</td></tr>)}</tbody></table></div><p className="caption">Scheduled times are local. Delay (15+ minutes) and cancellation rates cover the same route, operating carrier and month in 2025. Fare statistics use all matching 2022 quotes for the same route, carrier code and departure month; they are not prices for these flights. Marketing and operating carrier codes may differ.</p></> : <p className="status">No flights found for this search.</p>}</Status>}
      </Card>
      <Card><div className="section-heading"><div><h2>Ticket price trends</h2><p>Average fare by days before departure. Based on 2022 data.</p></div><span className="section-icon">↗</span></div>{search && <Status state={trends}><Bars data={trends.data} /></Status>}</Card>
    </div>
  </>;
}
