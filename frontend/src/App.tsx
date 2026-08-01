import { BrowserRouter, Routes, Route } from "react-router-dom";
import { WalletProvider } from "./lib/wallet-context";
import { Nav } from "./components/Nav";
import Landing from "./pages/Landing";
import Prophecies from "./pages/Prophecies";
import ProphecyDetail from "./pages/ProphecyDetail";
import Submit from "./pages/Submit";
import Portfolio from "./pages/Portfolio";
import Prophet from "./pages/Prophet";
import HowItWorks from "./pages/HowItWorks";
import "./styles/tokens.css";

export default function App() {
  return (
    <WalletProvider>
      <BrowserRouter>
        <div style={{ minHeight: "100vh" }}>
          <Nav />
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/prophecies" element={<Prophecies />} />
            <Route path="/prophecies/:id" element={<ProphecyDetail />} />
            <Route path="/submit" element={<Submit />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/prophet/:address" element={<Prophet />} />
            <Route path="/how-it-works" element={<HowItWorks />} />
          </Routes>
        </div>
      </BrowserRouter>
    </WalletProvider>
  );
}
