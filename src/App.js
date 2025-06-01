// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';
import Home from './Home';
import ImagePage from './Image';
import DenoisePage from './DenoisePage';

function AppContent() {
  const navigate = useNavigate();

  const handleDenoise = () => {
    navigate('/denoise');
  };

  return (
    <>
      <nav style={{ marginBottom: '10px' }}>
        <Link to="/">Home</Link> | <Link to="/image">Image</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/image" element={<ImagePage />} />
        <Route path="/denoise" element={<DenoisePage />} />
      </Routes>
    </>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;