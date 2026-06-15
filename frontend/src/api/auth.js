import api from './config';

export const login = async (email, password) => {
    const response = await api.post('/auth/login/', { email, password });
    return response.data;
};

export const register = async (name, email, password) => {
    const response = await api.post('/auth/register/', { name, email, password });
    return response.data;
};

export const getMe = async () => {
    const response = await api.get('/auth/me/');
    return response.data;
};
