import React, { useState } from "react";
import { useData, number, pct } from "../api";
import { Status, Card, Title, Select, Metric, Routes } from "../components";
function WeatherChart({ data }) {
  if (!data?.length) return <p className="status">No weather data available.</p>;
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const line = (key, max) => data.map((d, i) => d[key] == null ? null : `${40 + i * 46},${160 - Math.min(Number(d[key]) / max, 1) * 130}`).filter(Boolean).join(" ");
  return <div className="chart-wrap"><div className="legend"><span><i className="red" /> Delay rate</span><span><i className="pink" /> Cancellation rate</span><span><i className="blue" /> Monthly high °F</span></div><svg viewBox="0 0 590 195" role="img" aria-label="Monthly delay, cancellation and high temperature trends">{[30, 62, 95, 127, 160].map((y) => <line key={y} x1="40" y1={y} x2="550" y2={y} stroke="#e5edf4" />)}<polyline points={line("departure_delay_rate", 100)} fill="none" stroke="#ee655e" strokeWidth="3" /><polyline points={line("cancellation_rate", 100)} fill="none" stroke="#f3a1ae" strokeWidth="3" /><polyline points={line("monthly_max_temp_f", 120)} fill="none" stroke="#2670e9" strokeWidth="3" />{months.map((m, i) => <text key={m} x={40 + i * 46} y="184" textAnchor="middle">{m}</text>)}</svg><p className="caption">Lines use separate scales: rates 0–100%, temperature 0–120°F. Missing observations are omitted.</p></div>;
}
function Airports({ airports }) {
  const [code, setCode] = useState("PHL");
  const year = "2025";
  const [selected, setSelected] = useState(null);
  const base = selected ? `/airports/${selected.code}` : null;
  const summary = useData(base ? `${base}/overview?year=${selected.year}` : null), routes = useData(base ? `${base}/top-routes?limit=5&year=${selected.year}` : null), efficiency = useData(base ? `${base}/efficiency?year=${selected.year}` : null), weather = useData(base ? `${base}/weather-reliability?year=${selected.year}` : null);
  const s = summary.data, e = efficiency.data;
  return <><Title title="Explore airports" description="Get to know airport traffic, connectivity, and seasonal weather." /><Card className="selector selector-row"><Select label="Select an airport" value={code} onChange={setCode}>{(airports.data || []).length ? airports.data.map((a) => <option key={a.airport_code} value={a.airport_code}>{a.airport_code} · {a.city || "Unknown city"}</option>) : <option value="PHL">PHL · Philadelphia</option>}</Select><button className="primary" onClick={() => setSelected({ code, year })}>Search</button></Card>{selected ? <><Card className="profile airport-profile"><Status state={summary}><div className="airport-art"><span>✈</span><small>AIRPORT PROFILE</small><strong>{selected.code}</strong></div><div className="airport-info"><span className="eyebrow">AIRPORT OVERVIEW · {selected.year}</span><h2>{s?.city || "Airport"} <span className="muted">({selected.code})</span></h2><div className="metrics"><Metric icon="⌁" value={number(s?.total_scheduled_operations)} label="Scheduled operations" /><Metric icon="✈" value={number(s?.airlines_served)} label="Airlines served" /><Metric icon="◎" value={number(s?.destinations)} label="Destinations" /></div></div></Status></Card><div className="two-col"><Card><div className="section-heading"><div><h2>Busiest routes</h2></div><span className="pill">TOP 5</span></div><Routes state={routes} /></Card><Card><div className="section-heading"><div><h2>Airport efficiency</h2></div></div><Status state={efficiency}><div className="efficiency"><div><span>◷</span><p>Departure delay rate<strong>{pct(e?.departure_delay_rate)}</strong></p></div><div><span>⊗</span><p>Cancellation rate<strong>{pct(e?.cancellation_rate)}</strong></p></div><div><span>↗</span><p>Average taxi-out time<strong>{e?.avg_taxi_out_min == null ? "\u2014" : `${number(e.avg_taxi_out_min)} min`}</strong></p></div><div><span>↘</span><p>Average taxi-in time<strong>{e?.avg_taxi_in_min == null ? "\u2014" : `${number(e.avg_taxi_in_min)} min`}</strong></p></div></div></Status></Card></div><Card><div className="section-heading"><div><h2>Seasonal weather & flight reliability</h2></div></div><Status state={weather}><WeatherChart data={weather.data} /></Status></Card></> : null}</>;
}
var Airports_default = Airports;
export {
  Airports_default as default
};
