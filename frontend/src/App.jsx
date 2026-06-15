import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { getToken } from './api/config';

import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import GroupDetail from './pages/GroupDetail';
import ExpenseDetail from './pages/ExpenseDetail';

const PrivateRoute = ({ children }) => {
    const token = getToken();
    if (!token) {
        return <Navigate to="/login" replace />;
    }
    return children;
};

const App = () => {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                
                <Route path="/dashboard" element={
                    <PrivateRoute>
                        <Dashboard />
                    </PrivateRoute>
                } />
                
                <Route path="/groups/:id" element={
                    <PrivateRoute>
                        <GroupDetail />
                    </PrivateRoute>
                } />
                
                <Route path="/expenses/:id" element={
                    <PrivateRoute>
                        <ExpenseDetail />
                    </PrivateRoute>
                } />
            </Routes>
        </BrowserRouter>
    );
};

export default App;
