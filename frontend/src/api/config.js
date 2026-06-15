import axios from 'axios';

// In-memory token storage
let token = null;

export const setToken = (newToken) => {
    token = newToken;
};

export const getToken = () => token;

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
});

// Request interceptor to add Authorization header
api.interceptors.request.use(
    (config) => {
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor to handle 401
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            // Redirect to login if unauthorized
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default api;
