import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, ResourceItem } from '../types';
import { 
  Sparkles, 
  Send, 
  X, 
  Bot, 
  User, 
  Database, 
  HelpCircle, 
  CheckCircle2,
  Maximize2,
  Minimize2
} from 'lucide-react';

interface RagChatAssistantProps {
  isOpen: boolean;
  onClose: () => void;
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  resources: ResourceItem[];
}

export const RagChatAssistant: React.FC<RagChatAssistantProps> = ({
  isOpen,
  onClose,
  messages,
  onSendMessage,
  resources,
}) => {
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const samplePrompts = [
    'Where is the quietest study spot right now?',
    'Should I go to the Gym at 18:00 or wait until 20:00?',
    'Forecast Main Library occupancy for exam week',
    'Which Cafeteria line has the shortest queue time?',
  ];

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const handleSend = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim()) return;

    const query = inputText;
    setInputText('');
    setIsTyping(true);

    onSendMessage(query);

    setTimeout(() => {
      setIsTyping(false);
    }, 1200);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30 backdrop-blur-xs transition-opacity animate-fade-in">
      
      {/* Backdrop click to close */}
      <div className="flex-1" onClick={onClose} />

      {/* Drawer Body */}
      <div 
        className={`bg-white dark:bg-zinc-900 border-l border-zinc-200 dark:border-zinc-800 shadow-2xl h-full flex flex-col transition-all duration-300 ${
          isExpanded ? 'w-full sm:w-[600px]' : 'w-full sm:w-[420px]'
        }`}
      >
        
        {/* Drawer Header */}
        <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between bg-zinc-50 dark:bg-zinc-900/90">
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 rounded-lg bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900">
              <Sparkles className="w-4 h-4 text-cyan-400 dark:text-cyan-600" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                Campus Copilot
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-100 dark:bg-cyan-950 text-cyan-800 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800">
                  RAG Active
                </span>
              </h3>
              <p className="text-[11px] text-zinc-500 font-mono">
                IBM watsonx Vector Collection • Real-time Twin DB
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-1">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1.5 rounded-md hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-500 dark:text-zinc-400 transition-colors hidden sm:block"
              title={isExpanded ? "Narrow drawer" : "Expand drawer"}
            >
              {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-md hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-500 dark:text-zinc-400 transition-colors"
              title="Close drawer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Message Log */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          
          {messages.map((msg) => {
            const isUser = msg.sender === 'user';

            return (
              <div
                key={msg.id}
                className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
              >
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs ${
                    isUser
                      ? 'bg-zinc-800 text-white dark:bg-zinc-200 dark:text-zinc-900'
                      : 'bg-cyan-100 dark:bg-cyan-950 text-cyan-800 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800'
                  }`}
                >
                  {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                <div className={`space-y-1.5 max-w-[85%] ${isUser ? 'text-right' : 'text-left'}`}>
                  
                  {/* Message Bubble */}
                  <div
                    className={`p-3 rounded-xl text-xs leading-relaxed ${
                      isUser
                        ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 font-medium'
                        : 'bg-zinc-100 dark:bg-zinc-800/80 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700/80'
                    }`}
                  >
                    {msg.text}
                  </div>

                  {/* RAG Sources Citations */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200/80 dark:border-zinc-800 text-[10px] space-y-1 text-zinc-500 font-mono">
                      <div className="flex items-center gap-1 font-semibold text-zinc-700 dark:text-zinc-300">
                        <Database className="w-3 h-3 text-cyan-500" />
                        RAG Vector Sources Cited:
                      </div>
                      <ul className="list-disc list-inside space-y-0.5 pl-1">
                        {msg.sources.map((src, i) => (
                          <li key={i} className="truncate">{src}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Suggested Action Pills */}
                  {msg.suggestedActions && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {msg.suggestedActions.map((action, idx) => (
                        <button
                          key={idx}
                          onClick={() => onSendMessage(action)}
                          className="text-[10px] px-2.5 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 font-medium transition-colors text-left"
                        >
                          → {action}
                        </button>
                      ))}
                    </div>
                  )}

                  <div className="text-[9px] font-mono text-zinc-400 px-1">
                    {msg.timestamp}
                  </div>

                </div>
              </div>
            );
          })}

          {isTyping && (
            <div className="flex items-center space-x-2 text-xs text-zinc-400 font-mono p-2">
              <Sparkles className="w-3.5 h-3.5 text-cyan-500 animate-spin" />
              <span>Querying Campus Twin Vector Store...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Sample Prompts */}
        <div className="px-4 py-2 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
          <div className="text-[10px] font-mono text-zinc-400 mb-1.5 flex items-center gap-1">
            <HelpCircle className="w-3 h-3" />
            Quick Copilot Queries:
          </div>
          <div className="flex flex-wrap gap-1">
            {samplePrompts.map((prompt, index) => (
              <button
                key={index}
                onClick={() => onSendMessage(prompt)}
                className="text-[10px] px-2 py-1 rounded-md bg-white dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 transition-colors truncate max-w-full"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* Input Box */}
        <form onSubmit={handleSend} className="p-3 border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex gap-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Ask Copilot about occupancy, WiFi, or schedules..."
            className="flex-1 px-3 py-2 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:border-zinc-400 transition-colors"
          />
          <button
            type="submit"
            disabled={!inputText.trim()}
            className="px-3 py-2 rounded-lg bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-medium text-xs disabled:opacity-40 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors flex items-center gap-1 shrink-0"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>

      </div>
    </div>
  );
};
