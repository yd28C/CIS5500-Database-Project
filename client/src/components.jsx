import React from "react";
import { number } from "./api";
function Status({ state, children }) {
  if (state.loading) return <p className="status">Loading data…</p>;
  if (state.error) return <p className="status error" role="alert">{state.error}</p>;
  return children;
}
function Card({ children, className = "" }) {
  return <section className={`card ${className}`}>{children}</section>;
}
function Title({ eyebrow, title, description }) {
  return <div className="page-title"><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>;
}
function Select({ label, value, onChange, children }) {
  return <label><span>{label}</span><select value={value} onChange={(e) => onChange(e.target.value)}>{children}</select></label>;
}
function Metric({ label, value, icon }) {
  return <div className="metric"><span className="metric-icon">{icon}</span><strong>{value}</strong><span>{label}</span></div>;
}
function Routes({ state }) {
  return <Status state={state}>{state.data?.length ? <table><thead><tr><th>Route</th><th className="right">Flights</th></tr></thead><tbody>{state.data.map((r, i) => <tr key={i}><td><b>{r.origin_code}</b><span className="route-dash"> → </span><b>{r.destination_code}</b></td><td className="right">{number(r.number_of_flights)}</td></tr>)}</tbody></table> : <p className="status">No routes found.</p>}</Status>;
}
export {
  Card,
  Metric,
  Routes,
  Select,
  Status,
  Title
};
