import api from './config';

export const uploadCSV = async (groupId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(`/import/upload/`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        },
        params: { groupId } // Or maybe the endpoint requires it differently depending on backend
    });
    return response.data;
};

export const getReport = async (batchId) => {
    const response = await api.get(`/import/report/${batchId}/`);
    return response.data;
};

export const approveAnomaly = async (anomalyId) => {
    const response = await api.post(`/import/anomalies/${anomalyId}/approve/`);
    return response.data;
};
