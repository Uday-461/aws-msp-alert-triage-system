import React, { useState, useEffect } from 'react';
import { Settings, ChevronDown, ChevronUp, Save } from 'lucide-react';

interface SettingsPanelProps {
  onApiKeysChange: (openai: string, openrouter: string) => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({ onApiKeysChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [openaiKey, setOpenaiKey] = useState('');
  const [openrouterKey, setOpenrouterKey] = useState('');
  const [saved, setSaved] = useState(false);

  // Load keys from localStorage on mount
  useEffect(() => {
    const storedOpenai = localStorage.getItem('openai_api_key') || '';
    const storedOpenrouter = localStorage.getItem('openrouter_api_key') || '';
    setOpenaiKey(storedOpenai);
    setOpenrouterKey(storedOpenrouter);

    // Notify parent of stored keys
    if (storedOpenai || storedOpenrouter) {
      onApiKeysChange(storedOpenai, storedOpenrouter);
    }
  }, [onApiKeysChange]);

  const handleSave = () => {
    // Save to localStorage
    localStorage.setItem('openai_api_key', openaiKey);
    localStorage.setItem('openrouter_api_key', openrouterKey);

    // Notify parent
    onApiKeysChange(openaiKey, openrouterKey);

    // Show saved indicator
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleClear = () => {
    setOpenaiKey('');
    setOpenrouterKey('');
    localStorage.removeItem('openai_api_key');
    localStorage.removeItem('openrouter_api_key');
    onApiKeysChange('', '');
  };

  return (
    <div className="bg-white border-b border-gray-200">
      {/* Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Settings size={18} className="text-gray-600" />
          <span className="text-sm font-medium text-gray-700">
            API Settings (Optional)
          </span>
        </div>
        {isOpen ? (
          <ChevronUp size={18} className="text-gray-600" />
        ) : (
          <ChevronDown size={18} className="text-gray-600" />
        )}
      </button>

      {/* Content */}
      {isOpen && (
        <div className="px-4 pb-4 space-y-4">
          <p className="text-xs text-gray-600">
            Provide your own API keys for better performance. If not provided, demo keys will be used.
          </p>

          {/* OpenAI API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              OpenAI API Key
            </label>
            <input
              type="password"
              value={openaiKey}
              onChange={(e) => setOpenaiKey(e.target.value)}
              placeholder="sk-..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Used for RAG embeddings (text-embedding-3-small)
            </p>
          </div>

          {/* OpenRouter API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              OpenRouter API Key
            </label>
            <input
              type="password"
              value={openrouterKey}
              onChange={(e) => setOpenrouterKey(e.target.value)}
              placeholder="sk-or-v1-..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Used for chat responses (Qwen 2.5 7B Instruct)
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white text-sm font-medium rounded-md hover:bg-primary-600 transition-colors"
            >
              <Save size={16} />
              {saved ? 'Saved!' : 'Save Keys'}
            </button>
            <button
              onClick={handleClear}
              className="px-4 py-2 bg-gray-200 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-300 transition-colors"
            >
              Clear Keys
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SettingsPanel;
