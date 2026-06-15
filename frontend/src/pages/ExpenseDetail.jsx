import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getExpense } from '../api/expenses';
import { getMe } from '../api/auth';
import Navbar from '../components/Navbar';

const ExpenseDetail = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [expense, setExpense] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [currentUser, setCurrentUser] = useState(null);

    useEffect(() => {
        const loadData = async () => {
            try {
                const user = await getMe();
                setCurrentUser(user);
                const expData = await getExpense(id);
                setExpense(expData);
            } catch (err) {
                setError('Failed to load expense details.');
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, [id]);

    if (loading) return <div className="loading">Loading expense...</div>;
    if (error) return <div className="error-message">{error}</div>;
    if (!expense) return <div className="error-message">Expense not found.</div>;

    return (
        <div className="page-container">
            <Navbar userName={currentUser?.name || currentUser?.email} />
            <div className="content">
                <button className="btn-cancel" style={{marginBottom: '1rem'}} onClick={() => navigate(-1)}>
                    &larr; Back
                </button>

                <div className="expense-detail-card">
                    <h2>{expense.title || expense.description}</h2>
                    <div className="expense-meta-large">
                        <p><strong>Date:</strong> {new Date(expense.date).toLocaleDateString()}</p>
                        <p><strong>Total Amount:</strong> ₹{parseFloat(expense.amount).toFixed(2)} {expense.currency || 'INR'}</p>
                        <p><strong>Paid By:</strong> {expense.paid_by_name || 'Unknown'}</p>
                        <p><strong>Split Type:</strong> {expense.split_type}</p>
                    </div>

                    <h3>Splits Breakdown</h3>
                    <table className="splits-table">
                        <thead>
                            <tr>
                                <th>Member Name</th>
                                <th>Amount They Owe</th>
                                <th>Settled?</th>
                            </tr>
                        </thead>
                        <tbody>
                            {expense.splits && expense.splits.map((split, idx) => (
                                <tr key={idx}>
                                    <td>{split.user_name || split.user_email}</td>
                                    <td>₹{parseFloat(split.amount_owed).toFixed(2)}</td>
                                    <td>
                                        <span className={`status-badge ${split.is_settled ? 'settled' : 'unsettled'}`}>
                                            {split.is_settled ? 'Yes' : 'No'}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                            {(!expense.splits || expense.splits.length === 0) && (
                                <tr>
                                    <td colSpan="3">No split details available.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default ExpenseDetail;
