import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getGroups, createGroup } from '../api/groups';
import { getMe } from '../api/auth';
import Navbar from '../components/Navbar';

const Dashboard = () => {
    const [groups, setGroups] = useState([]);
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newGroupName, setNewGroupName] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        const fetchData = async () => {
            try {
                const userData = await getMe();
                setUser(userData);
                const groupsData = await getGroups();
                setGroups(groupsData);
            } catch (err) {
                setError('Failed to load dashboard data.');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleCreateGroup = async (e) => {
        e.preventDefault();
        try {
            const newGroup = await createGroup(newGroupName);
            setGroups([...groups, newGroup]);
            setShowCreateModal(false);
            setNewGroupName('');
        } catch (err) {
            alert('Failed to create group');
        }
    };

    if (loading) return <div className="loading">Loading dashboard...</div>;

    return (
        <div className="page-container">
            <Navbar userName={user?.name || user?.email} />
            <div className="content">
                <div className="dashboard-header">
                    <h2>Welcome, {user?.name || user?.email}</h2>
                    <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
                        Create Group
                    </button>
                </div>

                {error && <div className="error-message">{error}</div>}

                <div className="groups-list">
                    {groups.length === 0 ? (
                        <p>You are not in any groups yet.</p>
                    ) : (
                        groups.map(group => (
                            <div key={group.id} className="group-card" onClick={() => navigate(`/groups/${group.id}`)}>
                                <h3>{group.name}</h3>
                                <p>Members: {group.members_count || group.members?.length || 0}</p>
                                <p className={`balance ${group.my_balance >= 0 ? 'positive' : 'negative'}`}>
                                    Your Balance: ₹{parseFloat(group.my_balance || 0).toFixed(2)}
                                </p>
                            </div>
                        ))
                    )}
                </div>

                {showCreateModal && (
                    <div className="modal-overlay">
                        <div className="modal-content">
                            <h3>Create New Group</h3>
                            <form onSubmit={handleCreateGroup}>
                                <div className="form-group">
                                    <label>Group Name</label>
                                    <input 
                                        type="text" 
                                        value={newGroupName} 
                                        onChange={(e) => setNewGroupName(e.target.value)} 
                                        required 
                                    />
                                </div>
                                <div className="modal-actions">
                                    <button type="button" className="btn-cancel" onClick={() => setShowCreateModal(false)}>Cancel</button>
                                    <button type="submit" className="btn-primary">Create</button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Dashboard;
