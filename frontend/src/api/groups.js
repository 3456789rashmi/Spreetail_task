import api from './config';

export const getGroups = async () => {
    const response = await api.get('/groups/');
    return response.data;
};

export const createGroup = async (name) => {
    const response = await api.post('/groups/', { name });
    return response.data;
};

export const getGroup = async (id) => {
    const response = await api.get(`/groups/${id}/`);
    return response.data;
};

export const addMember = async (groupId, email) => {
    const response = await api.post(`/groups/${groupId}/members/`, { email });
    return response.data;
};

export const removeMember = async (groupId, userId) => {
    const response = await api.delete(`/groups/${groupId}/members/${userId}/`);
    return response.data;
};
