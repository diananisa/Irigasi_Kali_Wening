import { useState } from "react";
import "./App.css";

import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import DataBangunan from "./pages/DataBangunan";
import PetaJaringan from "./pages/PetaJaringan";

export default function App() {
  const [activePage, setActivePage] = useState("Dashboard");

  const renderPage = () => {
    switch (activePage) {
      case "Peta Jaringan":
        return <PetaJaringan />;
      case "Data Bangunan":
        return <DataBangunan />;
      case "Dashboard":
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="app-layout">
      <Sidebar
        activePage={activePage}
        onNavigate={setActivePage}
      />

      <main className="main-content">
        <Navbar activePage={activePage} />
        {renderPage()}
      </main>
    </div>
  );
}
