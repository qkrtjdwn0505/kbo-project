import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/layout/Navbar";
import Footer from "./components/layout/Footer";
import HomePage from "./pages/HomePage";
import ExplorerPage from "./pages/ExplorerPage";
import PlayerPage from "./pages/PlayerPage";
import StandingsPage from "./pages/StandingsPage";
import SchedulePage from "./pages/SchedulePage";

function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/explorer" element={<ExplorerPage />} />
          <Route path="/players" element={<PlayerPage />} />
          <Route path="/players/:id" element={<PlayerPage />} />
          <Route path="/standings" element={<StandingsPage />} />
          <Route path="/schedule" element={<SchedulePage />} />
        </Routes>
      </main>
      <Footer />
    </BrowserRouter>
  );
}

export default App;
