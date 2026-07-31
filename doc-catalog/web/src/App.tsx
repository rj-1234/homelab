import { Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Vault } from "@/pages/Vault";
import { Library } from "@/pages/Library";
import { DocDetail } from "@/pages/DocDetail";
import { Review } from "@/pages/Review";
import { Status } from "@/pages/Status";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Vault />} />
        <Route path="/library" element={<Library />} />
        <Route path="/doc/:id" element={<DocDetail />} />
        <Route path="/review" element={<Review />} />
        <Route path="/status" element={<Status />} />
      </Route>
    </Routes>
  );
}
