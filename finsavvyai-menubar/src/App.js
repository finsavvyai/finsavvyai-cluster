import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [clusterStatus, setClusterStatus] = useState(null);
  const [health, setHealth] = useState(null);
  const [models, setModels] = useState([]);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState('gpt-3.5-turbo');
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      // Load cluster status
      const status = await window.electronAPI?.invoke('get-cluster-status');
      if (status && !status.error) {
        setClusterStatus(status);
      }

      // Load health
      const healthData = await window.electronAPI?.invoke('get-health');
      if (healthData && !healthData.error) {
        setHealth(healthData);
      }

      // Load models
      const modelsData = await window.electronAPI?.invoke('get-models');
      if (modelsData && modelsData.data) {
        setModels(modelsData.data);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = { role: 'user', content: inputMessage };
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await window.electronAPI?.invoke('chat-completion',
        [...messages, userMessage],
        selectedModel
      );

      if (response && response.choices) {
        const assistantMessage = {
          role: 'assistant',
          content: response.choices[0].message.content
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        setMessages(prev => [...prev, {
          role: 'system',
          content: 'Error: Failed to get response from AI'
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'system',
        content: `Error: ${error.message}`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  const minimizeWindow = () => {
    window.electronAPI?.invoke('minimize-window');
  };

  const closeWindow = () => {
    window.electronAPI?.invoke('close-window');
  };

  return (
    <div className="App">
      {/* Title Bar */}
      <div className="title-bar">
        <div className="title-bar-content">
          <span>🤖 FinSavvyAI</span>
          <div className="title-bar-controls">
            <button onClick={minimizeWindow}>−</button>
            <button onClick={closeWindow}>×</button>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="tab-nav">
        <button
          className={activeTab === 'chat' ? 'active' : ''}
          onClick={() => setActiveTab('chat')}
        >
          💬 Chat
        </button>
        <button
          className={activeTab === 'cluster' ? 'active' : ''}
          onClick={() => setActiveTab('cluster')}
        >
          🏠 Cluster
        </button>
        <button
          className={activeTab === 'models' ? 'active' : ''}
          onClick={() => setActiveTab('models')}
        >
          🤖 Models
        </button>
      </div>

      {/* Chat Tab */}
      {activeTab === 'chat' && (
        <div className="tab-content">
          <div className="chat-messages">
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.role}`}>
                <strong>
                  {message.role === 'user' ? '👤 You:' :
                   message.role === 'assistant' ? '🤖 AI:' : '⚙️ System:'}
                </strong>
                <div className="message-content">{message.content}</div>
              </div>
            ))}
            {isLoading && <div className="message assistant">🤖 Thinking...</div>}
          </div>

          <div className="chat-input">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="model-select"
            >
              {models.map(model => (
                <option key={model.id} value={model.id}>
                  {model.id}
                </option>
              ))}
            </select>

            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Ask me anything..."
              disabled={isLoading}
              className="message-input"
            />

            <button
              onClick={sendMessage}
              disabled={isLoading || !inputMessage.trim()}
              className="send-button"
            >
              Send
            </button>

            <button onClick={clearChat} className="clear-button">
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Cluster Tab */}
      {activeTab === 'cluster' && (
        <div className="tab-content">
          <div className="cluster-info">
            <h3>🏠 Cluster Status</h3>

            {health ? (
              <div className="status-card">
                <h4>Health: <span className="status-healthy">✅ {health.status}</span></h4>
                <p>Provider: {health.provider}</p>
                <p>Version: {health.version}</p>
              </div>
            ) : (
              <div className="status-card">
                <h4>Health: <span className="status-unhealthy">❌ Offline</span></h4>
                <p>Start your cluster with: python3 cluster_master.py</p>
              </div>
            )}

            {clusterStatus && (
              <div className="status-card">
                <h4>Cluster Information</h4>
                <p>Nodes: {clusterStatus.online_nodes}/{clusterStatus.total_nodes}</p>
                <p>Models: {clusterStatus.total_models}</p>
                <p>Master: {clusterStatus.master}</p>
              </div>
            )}

            <div className="quick-actions">
              <h4>Quick Actions</h4>
              <button onClick={() => window.open('http://localhost:8001', '_blank')}>
                🌐 Open Web Dashboard
              </button>
              <button onClick={loadData}>
                🔄 Refresh Status
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Models Tab */}
      {activeTab === 'models' && (
        <div className="tab-content">
          <div className="models-info">
            <h3>🤖 Available Models</h3>

            {models.length > 0 ? (
              <div className="models-list">
                {models.map(model => (
                  <div key={model.id} className="model-card">
                    <h4>{model.id}</h4>
                    <p>{model.description}</p>
                    <p><small>Owned by: {model.owned_by}</small></p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-models">
                <p>No models available</p>
                <p>Start your cluster to load models</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
