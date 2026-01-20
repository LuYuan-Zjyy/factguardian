import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
});

export const uploadDocument = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const extractFacts = async (docId) => {
    // Note: The backend endpoint is /api/documents/{document_id}/extract-facts
    // But main.py uses post.
    const response = await api.post(`/documents/${docId}/extract-facts`);
    return response.data;
};

export const detectConflicts = async (docId) => {
    const response = await api.post(`/detect-conflicts/${docId}`);
    return response.data;
};

export const verifyFacts = async (docId) => {
    const response = await api.post(`/documents/${docId}/verify-facts`);
    return response.data;
};
