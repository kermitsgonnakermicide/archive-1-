import React from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import HomePage from "./pages/HomePage";
import AuthPage from "./pages/AuthPage";
import AdminPage from "./pages/AdminPage";
import EventDetailPage from "./pages/EventDetailPage";
import EventScholarshipPage from "./pages/EventScholarshipPage";
import EventRegisteredPage from "./pages/EventRegisteredPage";
import PaymentPage from "./pages/PaymentPage";
import PaymentSuccessPage from "./pages/PaymentSuccessPage";
import CustomPage from "./pages/CustomPage";
import { Toaster } from "sonner";

function Layout({ children }) {
  const { pathname } = useLocation();
  const bareRoutes = ["/login", "/signup", "/admin"];
  const bare = bareRoutes.some((r) => pathname.startsWith(r));
  return (
    <>
      {!bare && <Navbar />}
      <main>{children}</main>
      {!bare && <Footer />}
    </>
  );
}

function App() {
  return (
    <div className="App">
      <AppProvider>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<AuthPage mode="login" />} />
              <Route path="/signup" element={<AuthPage mode="signup" />} />
              <Route path="/admin" element={<AdminPage />} />
              <Route path="/events/:id" element={<EventDetailPage />} />
              <Route path="/events/:id/scholarship" element={<EventScholarshipPage />} />
              <Route path="/events/:id/registered" element={<EventRegisteredPage />} />
              <Route path="/payment/:registrationId" element={<PaymentPage />} />
              <Route path="/payment-success" element={<PaymentSuccessPage />} />
              <Route path="/p/:slug" element={<CustomPage />} />
            </Routes>
          </Layout>
          <Toaster position="top-right" richColors closeButton />
        </BrowserRouter>
      </AppProvider>
    </div>
  );
}

export default App;
