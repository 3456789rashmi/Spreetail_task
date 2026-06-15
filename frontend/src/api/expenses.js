import api from './config';

export const getExpenses = async (groupId) => {
    const response = await api.get(`/expenses/group/${groupId}/`);
    return response.data;
};

export const getExpense = async (id) => {
    const response = await api.get(`/expenses/detail/${id}/`);
    return response.data;
};

export const createExpense = async (groupId, data) => {
    const response = await api.post(`/expenses/group/${groupId}/`, data);
    return response.data;
};

export const getBalances = async (groupId) => {
    const response = await api.get(`/expenses/group/${groupId}/balances/`);
    return response.data;
};

export const createSettlement = async (data) => {
    const response = await api.post(`/expenses/settlements/`, data);
    return response.data;
};
