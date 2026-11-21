import React, { useState } from "react";
import { useData, number, money } from "../api";
import { Status, Card, Title, Select, Metric, Routes } from "../components";
function Airlines({ airlines }) {
  const [code, setCode] = useState("AA");
  const [selected, setSelected] = useState(null);
  const summary = useData(selected ? `/airlines/${selected}/summary` : null), routes = useData(selected ? `/airlines/${selected}/top-routes?limit=5` : null);
  const s = summary.data;
  return <><Title title="Explore airlines" description="Discover airline networks, pricing, and performance." /><Card className="selector selector-row"><Select label="Select an airline" value={code} onChange={setCode}>{(airlines.data || []).length ? airlines.data.map((a) => <option key={a.airline_code} value={a.airline_code}>{a.airline_name || a.airline_code} ({a.airline_code})</option>) : <option value="AA">American Airlines (AA)</option>}</Select><button className="primary" onClick={() => setSelected(code)}>Search</button></Card>{selected ? <><Card className="profile"><Status state={summary}><div className="profile-top"><div className="profile-icon">✈</div><div><span className="eyebrow">AIRLINE PROFILE</span><h2>{s?.airline_name || selected} <span className="muted">({selected})</span></h2><p>Explore this airline's network and historical nonstop fares.</p></div></div><div className="metrics"><Metric icon="◎" value={number(s?.cities_served)} label="Cities served" /><Metric icon="⌁" value={number(s?.airports_served)} label="Airports served" /><Metric icon="✈" value={number(s?.total_routes)} label="Routes" /><Metric icon="◇" value={money(s?.avg_ticket_price)} label="Average ticket price (2022)" /></div></Status></Card><div className="two-col"><Card><div className="section-heading"><div><h2>Top routes</h2><p>Most frequently operated routes</p></div><span className="pill">TOP 5</span></div><Routes state={routes} /></Card><Card><div className="section-heading"><div><h2>Reliability performance</h2><p>Historical airline performance</p></div></div><div className="empty-panel"><span>◷</span><strong>Coming soon</strong><p>Airline delay and cancellation data will appear here when the reliability API is available.</p></div></Card></div><Card><h2>Common causes of delays</h2><p className="subtext">Delay cause data will be available when the airline reliability API is connected.</p></Card></> : null}</>;
}
var Airlines_default = Airlines;
export {
  Airlines_default as default
};
