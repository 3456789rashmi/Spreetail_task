import React, { useState } from 'react';
import { createExpense } from '../api/expenses';

const AddExpenseModal = ({ groupId, members, onClose, onExpenseAdded }) => {
    const [title, setTitle] = useState('');
    const [amount, setAmount] = useState('');
    const [currency, setCurrency] = useState('INR');
    const [date, setDate] = useState('');
    const [paidBy, setPaidBy] = useState(members[0]?.id || '');
    const [splitType, setSplitType] = useState('equal');
    const [splitWith, setSplitWith] = useState(
        members.reduce((acc, member) => ({ ...acc, [member.id]: true }), {})
    );
    const [splitValues, setSplitValues] = useState({});
    
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleCheckboxChange = (memberId) => {
        setSplitWith(prev => ({ ...prev, [memberId]: !prev[memberId] }));
    };

    const handleSplitValueChange = (memberId, value) => {
        setSplitValues(prev => ({ ...prev, [memberId]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const data = {
                title,
                amount: parseFloat(amount),
                currency,
                date,
                paidBy,
                splitType,
                splitWith: Object.keys(splitWith).filter(id => splitWith[id]),
                splitValues
            };
            await createExpense(groupId, data);
            onExpenseAdded();
            onClose();
        } catch (err) {
            setError('Failed to add expense. Please check your inputs.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <h2>Add Expense</h2>
                {error && <div className="error-message">{error}</div>}
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Title</label>
                        <input type="text" value={title} onChange={e => setTitle(e.target.value)} required />
                    </div>
                    <div className="form-group row">
                        <div className="col">
                            <label>Amount</label>
                            <input type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} required />
                        </div>
                        <div className="col">
                            <label>Currency</label>
                            <select value={currency} onChange={e => setCurrency(e.target.value)}>
                                <option value="INR">INR</option>
                                <option value="USD">USD</option>
                            </select>
                        </div>
                    </div>
                    <div className="form-group">
                        <label>Date</label>
                        <input type="date" value={date} onChange={e => setDate(e.target.value)} required />
                    </div>
                    <div className="form-group">
                        <label>Paid By</label>
                        <select value={paidBy} onChange={e => setPaidBy(e.target.value)}>
                            {members.map(m => (
                                <option key={m.id} value={m.id}>{m.name || m.email}</option>
                            ))}
                        </select>
                    </div>
                    <div className="form-group">
                        <label>Split Type</label>
                        <select value={splitType} onChange={e => setSplitType(e.target.value)}>
                            <option value="equal">Equal</option>
                            <option value="exact">Exact Amount</option>
                            <option value="percentage">Percentage</option>
                            <option value="shares">Shares</option>
                        </select>
                    </div>

                    <div className="form-group split-with-group">
                        <label>Split With</label>
                        {members.map(m => (
                            <div key={m.id} className="split-member-row">
                                <label className="checkbox-label">
                                    <input 
                                        type="checkbox" 
                                        checked={splitWith[m.id] || false} 
                                        onChange={() => handleCheckboxChange(m.id)} 
                                    />
                                    {m.name || m.email}
                                </label>
                                {splitWith[m.id] && splitType !== 'equal' && (
                                    <input 
                                        type="number" 
                                        step="0.01"
                                        placeholder={splitType === 'exact' ? 'Amount' : splitType === 'percentage' ? '%' : 'Shares'}
                                        value={splitValues[m.id] || ''}
                                        onChange={(e) => handleSplitValueChange(m.id, e.target.value)}
                                        required
                                    />
                                )}
                            </div>
                        ))}
                    </div>

                    <div className="modal-actions">
                        <button type="button" className="btn-cancel" onClick={onClose} disabled={loading}>Cancel</button>
                        <button type="submit" className="btn-primary" disabled={loading}>
                            {loading ? 'Saving...' : 'Save Expense'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddExpenseModal;
