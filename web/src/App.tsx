import { HashRouter, Routes, Route, NavLink } from "react-router-dom";
import { useReport } from "./hooks/useReport";
import { HeadlineBar } from "./components/HeadlineBar";
import { FileDropZone } from "./components/FileDropZone";
import { Graveyard } from "./views/Graveyard";
import { Crypt } from "./views/Crypt";
import { Exorcism } from "./views/Exorcism";
import { About } from "./views/About";

function AppShell() {
  const report = useReport();

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="app-title">
          <span aria-hidden="true">⚰️</span>
          <h1>Graveyard Shift</h1>
          <span className="app-tagline">Your AWS zombie report</span>
        </div>

        <nav className="app-nav" aria-label="Main navigation">
          <NavLink to="/"         className={({ isActive }) => isActive ? "nav-link active" : "nav-link"} end>🪦 Graveyard</NavLink>
          <NavLink to="/crypt"    className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>🔍 Crypt</NavLink>
          <NavLink to="/exorcism" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>🔥 Exorcism</NavLink>
          <NavLink to="/about"    className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>📖 About</NavLink>
        </nav>
      </header>

      {/* Headline stats */}
      {report && <HeadlineBar summary={report.summary} demo={report.demo} />}

      {/* File drop zone */}
      <div className="app-filedrop">
        <FileDropZone />
      </div>

      {/* Main content */}
      <main className="app-main">
        {report ? (
          <Routes>
            <Route path="/"         element={<Graveyard report={report} />} />
            <Route path="/crypt"    element={<Crypt report={report} />} />
            <Route path="/exorcism" element={<Exorcism report={report} />} />
            <Route path="/about"    element={<About />} />
          </Routes>
        ) : (
          <div className="app-loading">
            <p>Loading graveyard…</p>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <span>Graveyard Shift — cost estimates are approximations. No data leaves your browser.</span>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <HashRouter>
      <AppShell />
    </HashRouter>
  );
}
