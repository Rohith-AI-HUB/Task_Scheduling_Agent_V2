import api from './api';

const pushService = {
  registerToken: async (token) => {
    const response = await api.post('/push/tokens', { token });
    return response.data;
  },

  unregisterToken: async (token) => {
    const response = await api.delete('/push/tokens', { data: { token } });
    return response.data;
  },
};

export default pushService;

