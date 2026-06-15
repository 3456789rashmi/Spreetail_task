import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { setToken } from '../api/config';

const Navbar = ({ userName }) => {
    const navigate = useNavigate();

    const handleLogout = () => {
        setToken(null);
        navigate('/login');
    };

    return (
        <nav className="navbar">
            <div className="navbar-brand">
                <Link to="/dashboard">SplitEase</Link>
            </div>
            <div className="navbar-menu">
                {userName && <span className="navbar-user">Hello, {userName}</span>}
                <Link to="/dashboard" className="navbar-link">Dashboard</Link>
                <button onClick={handleLogout} className="btn-logout">Logout</button>
            </div>
        </nav>
    );
};

export default Navbar;
