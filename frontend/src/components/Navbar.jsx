import { Bell, Search } from "lucide-react";

const pageInfo = {
  Dashboard: {
    title: "Dashboard",
    description: "Informasi kondisi jaringan irigasi",
  },
  "Peta Jaringan": {
    title: "Peta Jaringan",
    description: "Visualisasi jaringan irigasi Kali Wening",
  },
  "Data Bangunan": {
    title: "Data Bangunan",
    description: "Informasi dan pengelolaan aset bangunan irigasi",
  },
  "Prioritas Pemeliharaan": {
    title: "Prioritas Pemeliharaan",
    description: "Daftar bangunan berdasarkan prioritas penanganan",
  },
  "Kualitas Data": {
    title: "Kualitas Data",
    description: "Informasi validasi dan kualitas data irigasi",
  },
};

export default function Navbar({ activePage }) {
  const currentPage = pageInfo[activePage] || pageInfo.Dashboard;

  return (
    <header className="navbar">
      <div className="navbar-title">
        <h2>{currentPage.title}</h2>
        <p>{currentPage.description}</p>
      </div>

      <div className="navbar-actions">
        <div className="search-box">
          <Search size={18} />
          <input type="text" placeholder="Cari data..." />
        </div>

        <button className="notification-button">
          <Bell size={20} />
        </button>

        <div className="profile">
          <div className="profile-avatar">A</div>
          <div>
            <strong>Administrator</strong>
            <small>Pengelola Sistem</small>
          </div>
        </div>
      </div>
    </header>
  );
}