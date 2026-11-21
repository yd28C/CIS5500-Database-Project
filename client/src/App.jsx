import React, { useState } from "react";
import { useData } from "./api";
import Flights from "./pages/Flights";
import Airlines from "./pages/Airlines";
import Airports from "./pages/Airports";
function App() {
  const [page, setPage] = useState("Flights");
  const airports = useData("/airports"), airlines = useData("/airlines");
  return <><header><div className="nav-inner"><a className="brand" href="#flights" onClick={() => setPage("Flights")}><span>✈</span> Flight<span>Insights</span></a><nav aria-label="Main navigation">{["Flights", "Airlines", "Airports"].map((p) => <a key={p} href={`#${p.toLowerCase()}`} className={page === p ? "active" : ""} onClick={() => setPage(p)}>{p}</a>)}</nav></div></header><main>{page === "Flights" ? <Flights airports={airports} /> : page === "Airlines" ? <Airlines airlines={airlines} /> : <Airports airports={airports} />}<footer><span>✈ &nbsp; Flight Insights</span><span>Explore the data behind your journey.</span></footer></main></>;
}
;
var App_default = App;
export {
  App_default as default
};
