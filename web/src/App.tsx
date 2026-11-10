import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { ReceiptProvider } from "./components/Receipt";
import { Shell } from "./components/Shell";
import { ToastProvider } from "./components/ui";
import { useAuth } from "./lib/auth";
import { probe } from "./lib/llm";
import Ask from "./pages/Ask";
import Calendar from "./pages/Calendar";
import Child from "./pages/Child";
import Children from "./pages/Children";
import EventPage from "./pages/Event";
import Home from "./pages/Home";
import Inbox from "./pages/Inbox";
import Login from "./pages/Login";
import SchoolPage from "./pages/School";
import Schools from "./pages/Schools";
import SettingsPage from "./pages/Settings";
import UploadPage from "./pages/Upload";

export default function App() {
  const { user } = useAuth();
  useEffect(() => { if (user) void probe(); }, [user]);
  if (!user) return <ToastProvider><Login /></ToastProvider>;
  return (
    <ToastProvider>
      <ReceiptProvider>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<Home />} />
            <Route path="children" element={<Children />} />
            <Route path="children/:id" element={<Child />} />
            <Route path="schools" element={<Schools />} />
            <Route path="schools/:id" element={<SchoolPage />} />
            <Route path="calendar" element={<Calendar />} />
            <Route path="events/:id" element={<EventPage />} />
            <Route path="ask" element={<Ask />} />
            <Route path="inbox" element={<Inbox />} />
            <Route path="upload" element={<UploadPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </ReceiptProvider>
    </ToastProvider>
  );
}
