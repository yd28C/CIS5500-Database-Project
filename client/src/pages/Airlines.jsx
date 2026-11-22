import React, { useState } from "react";
import { useData, number, money, pct } from "../api";
import { Status, Card, Title, Select, Metric, Routes } from "../components";
function Airlines({ airlines }) {
  const [code, setCode] = useState("AA");
  const [selected, setSelected] = useState(null);
  const summary = useData(selected ? `/airlines/${selected}/summary` : null), routes = useData(selected ? `/airlines/${selected}/top-routes?limit=5` : null);
  const reliability = useData(selected ? `/airlines/${selected}/reliability` : null);
  const s = summary.data;
  const performance = reliability.data?.[0];
  const causes = performance ? [
    ['Carrier', performance.carrier_delay],
    ['Late aircraft', performance.late_aircraft_delay],
    ['Weather', performance.weather_delay],
    ['Air traffic system', performance.nas_delay],
    ['Security', performance.security_delay],
  ] : [];
  const totalMinutes = causes.reduce((sum, [, value]) => sum + (Number(value) || 0), 0);
  return <><Title title="Explore airlines" description="Discover airline networks, pricing, and performance." /><Card className="selector selector-row"><Select label="Select an airline" value={code} onChange={setCode}>{(airlines.data || []).length ? airlines.data.map((a) => <option key={a.airline_code} value={a.airline_code}>{a.airline_name || a.airline_code} ({a.airline_code})</option>) : <option value="AA">American Airlines (AA)</option>}</Select><button className="primary" onClick={() => setSelected(code)}>Search</button></Card>{selected ? <><Card className="profile"><Status state={summary}><div className="profile-top"><div className="profile-icon">✈</div><div><span className="eyebrow">AIRLINE PROFILE．2025</span><h2>{s?.airline_name || selected} <span className="muted">({selected})</span></h2></div></div><div className="metrics"><Metric icon="◎" value={number(s?.cities_served)} label="Cities served" /><Metric icon="⌁" value={number(s?.airports_served)} label="Airports served" /><Metric icon="✈" value={number(s?.total_routes)} label="Routes" /><Metric icon="$" value={money(s?.avg_ticket_price)} label="Average ticket price (2022)" /></div></Status></Card><div className="two-col"><Card><div className="section-heading"><div><h2>Top routes</h2></div><span className="pill">TOP 5</span></div><Routes state={routes} /></Card><Card><div className="section-heading"><div><h2>Reliability performance</h2></div></div><Status state={reliability}>{performance ? <><div className="efficiency"><div><p>On-time arrival rate<strong>{pct(performance.on_time_rate)}</strong></p></div><div><p>Arrival delay rate<strong>{pct(performance.delay_rate)}</strong></p></div><div><p>Cancellation rate<strong>{pct(performance.cancellation_rate)}</strong></p></div><div><p>Average positive arrival delay<strong>{performance.avg_delay_duration == null ? '—' : `${number(performance.avg_delay_duration)} min`}</strong></p></div></div><p className="caption">{number(performance.total_flights)} scheduled flights. Rates use all scheduled flights; on-time excludes cancelled and diverted flights.</p></> : <p className="status">No reliability data available for this airline.</p>}</Status></Card></div><Card><h2>Common causes of delays</h2><Status state={reliability}>{!performance ? <p className="status">No delay data available for this airline.</p> : totalMinutes === 0 ? <p className="status">No delay-cause minutes available.</p> : <div className="delay-causes">{causes.map(([label, value]) => { const share = (Number(value) || 0) / totalMinutes * 100; return <div className="delay-row" key={label}><span>{label}</span><div className="delay-track"><div className="delay-bar" style={{ width: `${share}%` }} /></div><strong>{share.toFixed(1)}%</strong><small>{number(value)} min</small></div>; })}</div>}</Status></Card></> : null}</>;
}
var Airlines_default = Airlines;
export {
  Airlines_default as default
};
