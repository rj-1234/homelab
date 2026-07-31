import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./styles/organic.css";
import "./styles/app.css";
import Compose from "./pages/Compose";
import Gift from "./pages/Gift";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Compose />} />
        <Route path="/g/:id" element={<Gift />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
