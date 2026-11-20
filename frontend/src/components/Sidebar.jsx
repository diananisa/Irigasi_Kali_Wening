import {
  LayoutDashboard,
  Map,
  Building2,
  ClipboardList,
  Database,
  Waves,
} from "lucide-react";

const menus = [
  { name: "Dashboard", icon: LayoutDashboard },
  { name: "Peta Jaringan", icon: Map },
  { name: "Data Bangunan", icon: Building2 },
  { name: "Prioritas Pemeliharaan", icon: ClipboardList },
  { name: "Kualitas Data", icon: Database },
];

export default function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon">
          <Waves size={25} />
        </div>

        <div>
          <h2>IRIGASI</h2>
          <span>KALI WENING</span>
        </div>
      </div>

      <div className="sidebar-label">MENU UTAMA</div>

      <nav className="sidebar-menu">
        {menus.map((menu) => {
          const Icon = menu.icon;
          const isActive = activePage === menu.name;

          return (
            <button
              type="button"
              key={menu.name}
              className={`menu-item ${isActive ? "active" : ""}`}
              onClick={() => onNavigate(menu.name)}
            >
              <Icon size={19} />
              <span>{menu.name}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <span className="status-indicator"></span>
        <div>
          <strong>Sistem Aktif</strong>
          <small>DI Kali Wening</small>
        </div>
      </div>
    </aside>
  );
}
