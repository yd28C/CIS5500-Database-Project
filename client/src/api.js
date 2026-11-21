import { useEffect, useState } from "react";
const api = async (path) => {
  const response = await fetch(`/api${path}`);
  if (!response.ok) throw new Error("Unable to load data. Check that the server and database are running.");
  return response.json();
};
const number = (n) => n == null ? "\u2014" : Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 });
const money = (n) => n == null ? "\u2014" : `$${number(n)}`;
const pct = (n) => n == null ? "\u2014" : `${number(n)}%`;
const time = (s) => s ? new Date(s).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "UTC" }) + " UTC" : "\u2014";
const duration = (d) => !d ? "\u2014" : typeof d === "string" ? d : `${d.days ? `${d.days}d ` : ""}${d.hours || 0}h ${d.minutes || 0}m`;
function useData(path) {
  const [state, setState] = useState({ loading: !!path, data: null, error: "" });
  useEffect(() => {
    if (!path) return;
    let live = true;
    setState({ loading: true, data: null, error: "" });
    api(path).then((data) => live && setState({ data, loading: false, error: "" })).catch((e) => live && setState({ data: null, loading: false, error: e.message }));
    return () => {
      live = false;
    };
  }, [path]);
  return state;
}
export {
  duration,
  money,
  number,
  pct,
  time,
  useData
};
