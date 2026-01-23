import api from './api';

/**
 * AI Service - Handles all AI-related API calls
 */
const aiService = {
  /**
   * Send a chat message to the AI assistant
   * @param {string} message - The user's message (max 500 chars)
   * @returns {Promise<Object>} Chat response with AI reply, intent, and context
   */
  sendChatMessage: async (message) => {
    const response = await api.post('/ai/chat', { message });
    return response.data;
  },

  /**
   * Get chat conversation history
   * @returns {Promise<Object>} Chat history with messages array
   */
  getChatHistory: async () => {
    const response = await api.get('/ai/chat/history');
    return response.data;
  },

  /**
   * Clear chat conversation history
   * @returns {Promise<Object>} Confirmation response
   */
  clearChatHistory: async () => {
    const response = await api.delete('/ai/chat/clear');
    return response.data;
  },

  /**
   * Get remaining AI credits for the current user
   * @returns {Promise<Object>} Credit status with remaining/limit/reset time
   */
  getCredits: async () => {
    const response = await api.get('/ai/credits');
    return response.data;
  },

  /**
   * Get AI-generated task schedule
   * @returns {Promise<Object>} AI schedule with prioritized tasks
   */
  getSchedule: async () => {
    const response = await api.get('/ai/schedule');
    return response.data;
  },

  /**
   * Get user context for AI (workload preferences, etc.)
   * @returns {Promise<Object>} User context data
   */
  getUserContext: async () => {
    const response = await api.get('/ai/context');
    return response.data;
  },

  /**
   * Update user context for AI
   * @param {Object} context - Context data to update
   * @returns {Promise<Object>} Updated context
   */
  updateUserContext: async (context) => {
    const response = await api.patch('/ai/context', context);
    return response.data;
  },

  /**
   * Optimize task schedule based on preferences
   * @param {Object} preferences - Optimization preferences
   * @returns {Promise<Object>} Optimized schedule
   */
  optimizeSchedule: async (preferences) => {
    const response = await api.post('/ai/schedule/optimize', preferences);
    return response.data;
  },

  // Extension Request Methods

  /**
   * Create a deadline extension request
   * @param {Object} requestData - Extension request data
   * @returns {Promise<Object>} Created extension request
   */
  createExtensionRequest: async (requestData) => {
    const response = await api.post('/extensions', requestData);
    return response.data;
  },

  /**
   * Get extension requests (filtered by role)
   * @param {string} status - Optional status filter (pending/approved/denied)
   * @returns {Promise<Object>} Extension requests list
   */
  getExtensionRequests: async (status = null) => {
    const params = status ? { status } : {};
    const response = await api.get('/extensions', { params });
    return response.data;
  },

  /**
   * Get specific extension request by ID
   * @param {string} extensionId - Extension request ID
   * @returns {Promise<Object>} Extension request details
   */
  getExtensionById: async (extensionId) => {
    const response = await api.get(`/extensions/${extensionId}`);
    return response.data;
  },

  /**
   * Approve an extension request (teacher only)
   * @param {string} extensionId - Extension request ID
   * @param {Object} reviewData - Review data (response, approved_deadline)
   * @returns {Promise<Object>} Updated extension request
   */
  approveExtension: async (extensionId, reviewData) => {
    const response = await api.patch(`/extensions/${extensionId}/approve`, reviewData);
    return response.data;
  },

  /**
   * Deny an extension request (teacher only)
   * @param {string} extensionId - Extension request ID
   * @param {Object} reviewData - Review data (response)
   * @returns {Promise<Object>} Updated extension request
   */
  denyExtension: async (extensionId, reviewData) => {
    const response = await api.patch(`/extensions/${extensionId}/deny`, reviewData);
    return response.data;
  },

  /**
   * Get extension request statistics (teacher only)
   * @returns {Promise<Object>} Extension statistics
   */
  getExtensionStats: async () => {
    const response = await api.get('/extensions/stats');
    return response.data;
  },
};

export default aiService;
