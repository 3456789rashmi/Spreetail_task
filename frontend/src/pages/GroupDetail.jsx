import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import AddExpenseModal from '../components/AddExpenseModal';
import { getGroup, addMember, removeMember } from '../api/groups';
import { getExpenses, getBalances, createSettlement } from '../api/expenses';
import { uploadCSV, approveAnomaly } from '../api/importer';
import { getMe } from '../api/auth';

const GroupDetail = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('expenses');
    const [group, setGroup] = useState(null);
    const [expenses, setExpenses] = useState([]);
    const [balances, setBalances] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showAddExpense, setShowAddExpense] = useState(false);
    
    // Members tab
    const [newMemberEmail, setNewMemberEmail] = useState('');
    
    // Import CSV tab
    const [csvFile, setCsvFile] = useState(null);
    const [importReport, setImportReport] = useState(null);
    const [importLoading, setImportLoading] = useState(false);

    // Current User
    const [currentUser, setCurrentUser] = useState(null);

    const loadGroupData = async () => {
        setLoading(true);
        setError('');
        try {
            const user = await getMe();
            setCurrentUser(user);
            
            const groupData = await getGroup(id);
            setGroup(groupData);
            
            if (activeTab === 'expenses') {
                const expensesData = await getExpenses(id);
                setExpenses(expensesData);
            } else if (activeTab === 'balances') {
                const balancesData = await getBalances(id);
                setBalances(balancesData);
            }
        } catch (err) {
            setError('Failed to load group details.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadGroupData();
    }, [id, activeTab]);

    const handleAddMember = async (e) => {
        e.preventDefault();
        try {
            await addMember(id, newMemberEmail);
            setNewMemberEmail('');
            loadGroupData(); // refresh
        } catch (err) {
            alert('Failed to add member.');
        }
    };

    const handleRemoveMember = async (userId) => {
        if(window.confirm('Are you sure you want to remove this member?')) {
            try {
                await removeMember(id, userId);
                loadGroupData();
            } catch (err) {
                alert('Failed to remove member.');
            }
        }
    };

    const handleSettleUp = async (balance) => {
        try {
            // Usually settling means the person who owes pays the person they owe
            await createSettlement({
                groupId: id,
                fromUserId: balance.from_user_id,
                toUserId: balance.to_user_id,
                amount: balance.amount
            });
            loadGroupData(); // refresh balances
        } catch (err) {
            alert('Failed to settle up.');
        }
    };

    const handleFileUpload = async (e) => {
        e.preventDefault();
        if (!csvFile) return;
        setImportLoading(true);
        try {
            const report = await uploadCSV(id, csvFile);
            setImportReport(report);
            setCsvFile(null);
        } catch (err) {
            alert('Failed to upload CSV.');
        } finally {
            setImportLoading(false);
        }
    };

    const handleApproveAnomaly = async (anomalyId) => {
        try {
            await approveAnomaly(anomalyId);
            // Re-fetch report or remove anomaly from state
            alert('Anomaly approved.');
            // Ideally we'd refresh the report here, or filter it out.
            setImportReport(prev => ({
                ...prev,
                anomalies: prev.anomalies.map(a => 
                    a.id === anomalyId ? { ...a, needs_approval: false, action_taken: 'Approved' } : a
                )
            }));
        } catch (err) {
            alert('Failed to approve anomaly.');
        }
    };

    if (loading && !group) return <div className="loading">Loading group...</div>;
    if (!group) return <div className="error-message">Group not found.</div>;

    return (
        <div className="page-container">
            <Navbar userName={currentUser?.name || currentUser?.email} />
            <div className="content">
                <div className="group-header">
                    <h2>{group.name}</h2>
                </div>

                {error && <div className="error-message">{error}</div>}

                <div className="tabs">
                    <button className={activeTab === 'expenses' ? 'active' : ''} onClick={() => setActiveTab('expenses')}>Expenses</button>
                    <button className={activeTab === 'balances' ? 'active' : ''} onClick={() => setActiveTab('balances')}>Balances</button>
                    <button className={activeTab === 'members' ? 'active' : ''} onClick={() => setActiveTab('members')}>Members</button>
                    <button className={activeTab === 'import' ? 'active' : ''} onClick={() => setActiveTab('import')}>Import CSV</button>
                </div>

                <div className="tab-content">
                    {activeTab === 'expenses' && (
                        <div>
                            <div className="tab-header">
                                <h3>Expenses</h3>
                                <button className="btn-primary" onClick={() => setShowAddExpense(true)}>Add Expense</button>
                            </div>
                            {loading ? <div className="loading">Loading...</div> : (
                                <ul className="expense-list">
                                    {expenses.length === 0 ? <p>No expenses yet.</p> : expenses.map(exp => (
                                        <li key={exp.id} className="expense-item" onClick={() => navigate(`/expenses/${exp.id}`)}>
                                            <div className="expense-info">
                                                <strong>{exp.title || exp.description}</strong>
                                                <span>{new Date(exp.date).toLocaleDateString()}</span>
                                            </div>
                                            <div className="expense-meta">
                                                <span>Paid by: {exp.paid_by_name || 'Someone'}</span>
                                                <span>Split: {exp.split_type}</span>
                                            </div>
                                            <div className="expense-amount">
                                                ₹{parseFloat(exp.amount).toFixed(2)}
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    )}

                    {activeTab === 'balances' && (
                        <div>
                            <h3>Balances</h3>
                            {loading ? <div className="loading">Loading...</div> : (
                                <div className="balances-list">
                                    {balances.length === 0 ? <p>Everyone is settled up!</p> : balances.map((bal, idx) => (
                                        <div key={idx} className="balance-item">
                                            <span><strong>{bal.from_user_name}</strong> owes <strong>{bal.to_user_name}</strong> ₹{parseFloat(bal.amount).toFixed(2)}</span>
                                            <button className="btn-primary btn-small" onClick={() => handleSettleUp(bal)}>Settle Up</button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'members' && (
                        <div>
                            <h3>Members</h3>
                            <form className="add-member-form" onSubmit={handleAddMember}>
                                <input 
                                    type="email" 
                                    placeholder="Member Email" 
                                    value={newMemberEmail} 
                                    onChange={e => setNewMemberEmail(e.target.value)} 
                                    required 
                                />
                                <button type="submit" className="btn-primary">Add Member</button>
                            </form>
                            <ul className="member-list">
                                {group.members?.map(m => (
                                    <li key={m.id} className={`member-item ${m.left_date ? 'past-member' : ''}`}>
                                        <div className="member-info">
                                            <strong>{m.name || m.email}</strong>
                                            <span className="joined-date">Joined: {new Date(m.joined_date || m.created_at).toLocaleDateString()}</span>
                                            {m.left_date && <span className="left-date">Left: {new Date(m.left_date).toLocaleDateString()}</span>}
                                        </div>
                                        {!m.left_date && m.id !== currentUser?.id && (
                                            <button className="btn-cancel btn-small" onClick={() => handleRemoveMember(m.id)}>Remove</button>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {activeTab === 'import' && (
                        <div>
                            <h3>Import CSV</h3>
                            <form className="import-form" onSubmit={handleFileUpload}>
                                <input 
                                    type="file" 
                                    accept=".csv" 
                                    onChange={e => setCsvFile(e.target.files[0])} 
                                    required 
                                />
                                <button type="submit" className="btn-primary" disabled={importLoading || !csvFile}>
                                    {importLoading ? 'Uploading...' : 'Upload'}
                                </button>
                            </form>

                            {importReport && (
                                <div className="import-report">
                                    <h4>Import Report</h4>
                                    <div className="report-summary">
                                        <p>Processed: {importReport.rows_processed || 0}</p>
                                        <p>Imported: {importReport.rows_imported || 0}</p>
                                        <p>Skipped/Anomalies: {importReport.rows_skipped || importReport.anomalies?.length || 0}</p>
                                    </div>
                                    
                                    {importReport.anomalies && importReport.anomalies.length > 0 && (
                                        <table className="anomalies-table">
                                            <thead>
                                                <tr>
                                                    <th>Row</th>
                                                    <th>Type</th>
                                                    <th>Description</th>
                                                    <th>Action</th>
                                                    <th>Approval</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {importReport.anomalies.map(anomaly => (
                                                    <tr key={anomaly.id}>
                                                        <td>{anomaly.row_number}</td>
                                                        <td>{anomaly.type}</td>
                                                        <td>{anomaly.description}</td>
                                                        <td>{anomaly.action_taken}</td>
                                                        <td>
                                                            {anomaly.needs_approval ? (
                                                                <button className="btn-primary btn-small" onClick={() => handleApproveAnomaly(anomaly.id)}>
                                                                    Approve
                                                                </button>
                                                            ) : (
                                                                <span>-</span>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {showAddExpense && (
                    <AddExpenseModal 
                        groupId={id} 
                        members={group.members?.filter(m => !m.left_date) || []} 
                        onClose={() => setShowAddExpense(false)} 
                        onExpenseAdded={() => {
                            if (activeTab === 'expenses') loadGroupData();
                            else setActiveTab('expenses');
                        }}
                    />
                )}
            </div>
        </div>
    );
};

export default GroupDetail;
